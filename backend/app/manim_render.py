"""
Manim renderer — real video when available, browser storyboard otherwise (v0.4.5b)
==================================================================================
Backs the design's north-star goal 10 and the ``<manim>`` blocks a line-analysis
(assistant.py) or the tutor can emit. Turns a math idea into an actual animated MP4
using **Manim Community Edition** when the server has it (plus ffmpeg); when it does
NOT, it degrades — returning the AI/template Manim code + a browser storyboard so the
frontend animates in-page instead. Same graceful-degradation contract as
``claude_service`` / ``recognize`` (the app always runs, configured or not).

Pure orchestration + subprocess (no FastAPI): the ``POST /manim/render`` route in
main.py builds the storyboard fallback (via its template ``ManimAnimator``) and
delegates the real render here — mirroring the assistant.py / workspace.py split.
"""

from __future__ import annotations

import os
import re
import sys
import glob
import shutil
import secrets
import subprocess
from typing import Any, Dict, Optional

from . import config
from . import prompts
from .claude_service import claude_service, ClaudeError

# Rendered clips are served as static files (StaticFiles mount in main.py). One dir
# under the shared data/ tree, like the other sqlite DBs live there.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MEDIA_DIR = os.path.join(DATA_DIR, "manim_media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# URL prefix the StaticFiles mount serves MEDIA_DIR under.
MEDIA_URL = "/manim-media"

# Rendering is heavy; cap it so a bad scene can't wedge a worker thread forever.
RENDER_TIMEOUT = int(os.environ.get("MANIM_RENDER_TIMEOUT", "150"))

_SCENE_RE = re.compile(r"class\s+(\w+)\s*\(\s*Scene\s*\)")
_DEFAULT_SCENE = "SolveScene"

# Any of these mobjects typeset via LaTeX (manim shells out to `latex`/`dvisvgm`).
# `Title` too — it subclasses Tex. Scenes using only Text/MarkupText need no LaTeX.
_TEX_RE = re.compile(r"\b(?:MathTex|Tex|Title|TransformMatchingTex)\b")
# Cross-platform LaTeX front-ends, in rough order of preference for a probe.
_LATEX_BINS = ("latex", "xelatex", "pdflatex", "lualatex")


def available() -> bool:
    """True only when BOTH the manim CLI and ffmpeg are on PATH — the two things a
    real render needs. When false, callers fall back to the browser storyboard.

    Note: LaTeX is checked separately (``latex_available``) because Text-only scenes
    render fine without it — we only require it for MathTex/Tex scenes."""
    return shutil.which("manim") is not None and shutil.which("ffmpeg") is not None


def latex_available() -> bool:
    """True when a LaTeX front-end is on PATH. Required for MathTex/Tex/Title scenes
    (manim invokes ``latex`` + ``dvisvgm`` to typeset formulas). Cross-platform:
    works via ``shutil.which`` regardless of MiKTeX / TeX Live / MacTeX / TinyTeX."""
    return any(shutil.which(b) is not None for b in _LATEX_BINS)


def _needs_latex(code: str) -> bool:
    """Does this scene use a LaTeX-backed mobject? Cheap static check so we can fail
    fast with a clear message instead of a cryptic subprocess traceback."""
    return bool(_TEX_RE.search(code or ""))


def latex_install_hint() -> str:
    """Per-OS, actionable install guidance — surfaced when a MathTex/Tex scene can't
    render because no LaTeX distribution is present (keeps the app portable)."""
    if sys.platform.startswith("win"):
        return "请安装 LaTeX：`choco install miktex`（或 MiKTeX/TeX Live 安装包）。"
    if sys.platform == "darwin":
        return "请安装 LaTeX：`brew install --cask mactex-no-gui`（或 TinyTeX）。"
    return "请安装 LaTeX：`apt install texlive-latex-extra texlive-fonts-extra dvisvgm`（或 TinyTeX）。"


def status() -> Dict[str, Any]:
    return {
        "available": available(),
        "manim": shutil.which("manim") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "latex": latex_available(),
        "media_dir": MEDIA_DIR,
    }


def _strip_code_fences(text: str) -> str:
    """Remove a leading ```python / ``` fence and a trailing ``` if the model wrapped
    its code despite being told not to."""
    t = (text or "").strip()
    t = re.sub(r"^```(?:python)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _detect_scene(code: str) -> Optional[str]:
    m = _SCENE_RE.search(code or "")
    return m.group(1) if m else None


def generate_code(spec: str = "", expression: str = "",
                  scene_name: str = _DEFAULT_SCENE,
                  session_id: str = "manim", model: Optional[str] = None) -> str:
    """Ask Claude for a self-contained Manim CE Scene (v0.4.5b). Returns "" on any
    failure so the caller can fall back to the template code."""
    if not claude_service.available():
        return ""
    try:
        system = prompts.build_manim_prompt(expression, spec=spec, scene_name=scene_name)
        text = claude_service.complete(
            system=system,
            messages=[{"role": "user", "content": "请只输出可运行的 Manim CE Python 代码。"}],
            model=model, session_id=session_id, max_tokens=1500, temperature=0.2,
        )
        return _strip_code_fences(text)
    except ClaudeError:
        return ""


def render(*,
           manim_code: Optional[str] = None,
           spec: str = "",
           expression: str = "",
           template_code: Optional[str] = None,
           scene_name: str = _DEFAULT_SCENE,
           session_id: str = "manim",
           model: Optional[str] = None,
           timeout: Optional[int] = None) -> Dict[str, Any]:
    """Produce a real MP4 for the animation, or degrade to the storyboard.

    Code source, in order: an explicit ``manim_code`` → AI-generated (Claude) →
    ``template_code`` (the SymPy-driven template the route passes in). Returns a dict
    with ``status`` one of:
      • ``ok``          — rendered; ``video_url`` points at the served MP4.
      • ``unavailable`` — Manim/ffmpeg not installed (frontend uses the storyboard).
      • ``error``       — render was attempted but failed/timed out (storyboard used).
    Always includes ``manim_code`` + ``provider`` so the UI can show/offer the code.
    """
    provider = ""
    code = _strip_code_fences(manim_code or "")
    if code:
        provider = "provided"
    if not code:
        ai = generate_code(spec, expression, scene_name=scene_name,
                           session_id=session_id, model=model)
        if ai:
            code, provider = ai, "claude"
    if not code:
        code = (template_code or "").strip()
        if code:
            provider = "template"

    scene = _detect_scene(code) or scene_name

    if not available():
        return {"status": "unavailable", "manim_code": code, "provider": provider,
                "scene": scene,
                "reason": "服务器未安装 Manim CE / ffmpeg，已回退到浏览器故事板。"}
    if not code:
        return {"status": "unavailable", "manim_code": "", "provider": provider,
                "scene": scene, "reason": "没有可渲染的 Manim 代码。"}

    # Fast fail: a MathTex/Tex scene without a LaTeX distro will spend seconds only to
    # die with a `latex not found` traceback. Detect it up front and return a clear,
    # actionable reason so the frontend degrades to the storyboard immediately. Keeps
    # the app portable — the same message guides install on Win / macOS / Linux.
    if _needs_latex(code) and not latex_available():
        return {"status": "error", "manim_code": code, "provider": provider,
                "scene": scene, "latex_missing": True,
                "reason": "该动画包含数学公式（MathTex/Tex），需要 LaTeX 才能渲染，"
                          f"当前环境未检测到 LaTeX。{latex_install_hint()}"
                          "已回退到浏览器故事板。"}

    return _render_subprocess(code, scene, timeout or RENDER_TIMEOUT, provider)


# Rich renders tracebacks inside box-drawing frames; strip that furniture so the real
# error line survives the `[-600:]` tail slice instead of a wall of │ ─ ┌ characters.
_BOX_CHARS = "─│┌┐└┘├┤┬┴┼╭╮╰╯━┃"


def _clean_tail(raw: str, limit: int = 500) -> str:
    """Distil manim's (often Rich-boxed) output down to its meaningful tail: drop box
    border lines, strip frame characters, collapse blank runs, keep the last `limit`."""
    lines = []
    for ln in (raw or "").splitlines():
        stripped = ln.strip().strip("|").strip()
        # Skip pure-border rows (e.g. `+----+`, `╭───╮`) and empty lines.
        if not stripped or all(c in _BOX_CHARS + "+-= " for c in stripped):
            continue
        lines.append(stripped.strip(_BOX_CHARS + "| ").strip())
    text = " ".join(l for l in lines if l).strip()
    return text[-limit:]


def _render_subprocess(code: str, scene: str, timeout: int, provider: str) -> Dict[str, Any]:
    """Write the scene to a temp dir, invoke `manim -ql`, copy the MP4 into the served
    MEDIA_DIR. Never raises — failures come back as ``status:"error"``."""
    import tempfile
    work = tempfile.mkdtemp(prefix="manim_")
    scene_file = os.path.join(work, "scene.py")
    tmp_media = os.path.join(work, "media")
    try:
        with open(scene_file, "w", encoding="utf-8") as fh:
            fh.write(code)
        cmd = ["manim", "-ql", "--format", "mp4", "--media_dir", tmp_media, scene_file, scene]
        # errors="replace": manim's output can mix encodings on Windows; never let a
        # decode error mask the real failure with a generic "渲染出错".
        proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
        if proc.returncode != 0:
            raw = f"{proc.stderr or ''}\n{proc.stdout or ''}"
            # A LaTeX compile/lookup failure (missing distro, missing package, bad
            # formula) is by far the most common cause — surface it plainly.
            low = raw.lower()
            # Signatures of a distro/binary being absent vs. a compile-time failure.
            _MISSING = ("winerror 2", "no such file", "not found", "returned non-zero")
            _COMPILE = ("latex compilation error", "missing $", "! ", "undefined control")
            if _needs_latex(code) and (
                not latex_available()
                or ("latex" in low and any(s in low for s in _MISSING))
                or any(s in low for s in _COMPILE)
            ):
                hint = latex_install_hint() if not latex_available() else \
                    "LaTeX 已安装但编译失败（可能缺少宏包，或公式 LaTeX 语法有误）。"
                return {"status": "error", "manim_code": code, "provider": provider,
                        "scene": scene, "latex_missing": not latex_available(),
                        "reason": f"数学公式渲染失败（LaTeX）。{hint}已回退到浏览器故事板。"}
            return {"status": "error", "manim_code": code, "provider": provider,
                    "scene": scene,
                    "reason": f"Manim 渲染失败：{_clean_tail(raw) or '未知错误'}"}
        # Locate the produced mp4 (manim writes under media/videos/<stem>/<quality>/).
        mp4s = glob.glob(os.path.join(tmp_media, "videos", "**", "*.mp4"), recursive=True)
        if not mp4s:
            return {"status": "error", "manim_code": code, "provider": provider,
                    "scene": scene, "reason": "渲染完成但未找到输出视频。"}
        mp4s.sort(key=os.path.getmtime)
        out_name = f"manim_{secrets.token_hex(6)}.mp4"
        shutil.copyfile(mp4s[-1], os.path.join(MEDIA_DIR, out_name))
        return {"status": "ok", "video_url": f"{MEDIA_URL}/{out_name}",
                "manim_code": code, "provider": provider, "scene": scene}
    except subprocess.TimeoutExpired:
        return {"status": "error", "manim_code": code, "provider": provider,
                "scene": scene, "reason": f"Manim 渲染超时（>{timeout}s）。"}
    except Exception as exc:  # pragma: no cover — defensive: any unexpected failure degrades
        return {"status": "error", "manim_code": code, "provider": provider,
                "scene": scene, "reason": f"渲染出错：{exc}"}
    finally:
        shutil.rmtree(work, ignore_errors=True)
