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


def available() -> bool:
    """True only when BOTH the manim CLI and ffmpeg are on PATH — the two things a
    real render needs. When false, callers fall back to the browser storyboard."""
    return shutil.which("manim") is not None and shutil.which("ffmpeg") is not None


def status() -> Dict[str, Any]:
    return {
        "available": available(),
        "manim": shutil.which("manim") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
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

    return _render_subprocess(code, scene, timeout or RENDER_TIMEOUT, provider)


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
        proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip()[-600:]
            return {"status": "error", "manim_code": code, "provider": provider,
                    "scene": scene, "reason": f"Manim 渲染失败：{tail or '未知错误'}"}
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
