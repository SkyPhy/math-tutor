"""
AI assistant — line-by-line analysis orchestration (v0.4.3a)
============================================================
Backs the ④ AI 助手屏 (`docs/DEVELOPMENT_PLAN.md` §C4 / §E2). Takes the student's
recognised-and-corrected work (handed over from the ③ 校对屏) plus the problem, splits
the work into lines, and asks Claude to produce an analysis **aligned to each line**:
a note only where a line has an error or an improvable point, and NOTHING where the
step is fine — so the assistant's right column stays blank on the correct rows
(the acceptance rule "无误行留空").

Layering (per §E2): the core goes through ``claude_service``; when the gateway is
down we degrade to a template result so the screen still works. Per-line follow-up
(``ask``) reuses the /claude/chat plumbing with the focused line + its analysis as
extra grounding, plus the render_mode / special-symbol constraints the shared chat
control needs.

Pure orchestration (no DB, no FastAPI): the thin ``/assistant/*`` routes in main.py
delegate here, mirroring the workspace.py precedent (v0.4.2a) where new logic lives
in its own module and the route decorators stay in main.py.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from . import config
from . import prompts
from .claude_service import claude_service, ClaudeError

# One tutor batch (all lines analysed in a single call) is short — well under the
# exam-generation budget but more than a chat reply.
_ANALYZE_MAX_TOKENS = 2000
_ANALYZE_TEMPERATURE = 0.3          #批改要稳，低温度

_TEMPLATE_SUMMARY = (
    "AI 老师暂时不可用（网关未配置或熔断中），已按行列出你的作答，"
    "但未逐行点评。稍后可再试「重新分析」。"
)

# Valid JSON string escapes; any other backslash (raw LaTeX like \frac, \times) is
# illegal JSON — double it so LaTeX-laden model output parses instead of being dropped.
_VALID_JSON_ESCAPE = set('"\\/bfnrtu')

# <manim>…</manim> storyboard note the model may append to a tricky line's analysis.
_MANIM_RE = re.compile(r"<manim>(.*?)</manim>", re.S)


def _repair_json_backslashes(t: str) -> str:
    """Double any backslash that isn't a valid JSON escape (mirrors main.py's
    repair) so LaTeX in the analysis strings doesn't break json.loads."""
    out: List[str] = []
    i, n = 0, len(t)
    while i < n:
        c = t[i]
        if c == "\\" and i + 1 < n and t[i + 1] not in _VALID_JSON_ESCAPE:
            out.append("\\\\")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Pull a JSON object out of a model response (tolerate fences / prose / raw
    LaTeX backslashes). Returns the dict, or None if nothing usable was found."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        return None
    frag = t[start:end + 1]
    for candidate in (frag, _repair_json_backslashes(frag)):
        try:
            obj = json.loads(candidate)
            return obj if isinstance(obj, dict) else None
        except Exception:
            continue
    return None


def split_lines(work_md: str) -> List[str]:
    """Split the student's work into the non-blank lines we analyse (1-based idx is
    just the position in this list). Blank lines are dropped so empty rows don't get
    spurious analysis; the surviving lines keep their original (stripped) text."""
    lines: List[str] = []
    for raw in (work_md or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        s = raw.strip()
        if s:
            lines.append(s)
    return lines


def _extract_manim(text: str) -> Tuple[str, Optional[str]]:
    """Lift a ``<manim>…</manim>`` storyboard note out of an analysis string,
    returning (analysis_without_the_block, storyboard_or_None)."""
    if not text:
        return text, None
    m = _MANIM_RE.search(text)
    if not m:
        return text, None
    spec = m.group(1).strip()
    cleaned = _MANIM_RE.sub("", text).strip()
    return cleaned, (spec or None)


def _base_rows(lines: List[str]) -> List[Dict[str, Any]]:
    """The aligned skeleton: one row per line, all "no issue" until the model fills
    analysis in. This is also exactly the template-fallback shape."""
    return [
        {"idx": i + 1, "content": c, "analysis": "", "has_issue": False, "manim": None}
        for i, c in enumerate(lines)
    ]


def analyze(problem: str,
            student_work_md: str,
            *,
            session_id: str = "assistant",
            model: Optional[str] = None,
            render_mode: Optional[str] = None) -> Dict[str, Any]:
    """Produce line-aligned analysis for the student's work.

    Returns ``{lines, summary, provider}`` where ``lines`` is one row per non-blank
    student line — ``{idx, content, analysis, has_issue, manim}`` — with analysis
    filled ONLY on rows that have an issue (correct rows stay blank). ``provider`` is
    ``claude:<model>`` when the gateway answered, else ``template`` (with a ``reason``).
    """
    lines = split_lines(student_work_md)
    if not lines:
        return {"lines": [], "summary": "还没有可分析的作答内容。", "provider": "empty"}

    rows = _base_rows(lines)

    if not claude_service.available():
        return {"lines": rows, "summary": _TEMPLATE_SUMMARY, "provider": "template",
                "reason": "gateway unavailable"}

    try:
        system = prompts.build_line_analysis_prompt(problem, lines, render_mode=render_mode)
        text = claude_service.complete(
            system=system,
            messages=[{"role": "user", "content": "请逐行分析这份作答，只输出 JSON 对象。"}],
            model=model, session_id=session_id,
            max_tokens=_ANALYZE_MAX_TOKENS, temperature=_ANALYZE_TEMPERATURE,
        )
    except ClaudeError as e:
        return {"lines": rows, "summary": _TEMPLATE_SUMMARY, "provider": "template",
                "reason": str(e)}

    obj = _parse_json_object(text)
    if not obj:
        # Gateway answered but the payload was unparseable — honest fallback rather
        # than pretending we graded it.
        return {"lines": rows, "summary": "AI 返回的分析无法解析，已按行列出你的作答。",
                "provider": "template", "reason": "unparseable analysis"}

    # Align the model's per-line notes back onto OUR rows (idx + content are the
    # source of truth), so a dropped/extra line can't misalign the table.
    by_idx: Dict[int, Dict[str, Any]] = {}
    for it in (obj.get("lines") or []):
        if isinstance(it, dict) and isinstance(it.get("idx"), int):
            by_idx[it["idx"]] = it

    for row in rows:
        it = by_idx.get(row["idx"])
        if not it:
            continue
        analysis = (it.get("analysis") or "").strip()
        analysis, manim = _extract_manim(analysis)
        # An explicit `manim` field wins over an inline <manim> block if both appear.
        if isinstance(it.get("manim"), str) and it["manim"].strip():
            manim = it["manim"].strip()
        # A non-empty analysis IS an issue even if the model forgot the flag.
        row["analysis"] = analysis
        row["has_issue"] = bool(it.get("has_issue")) or bool(analysis)
        row["manim"] = manim or None

    summary = (obj.get("summary") or "").strip()
    if not summary:
        n_issues = sum(1 for r in rows if r["has_issue"])
        summary = (f"共 {len(rows)} 行，其中 {n_issues} 行有可改进点。"
                   if n_issues else f"共 {len(rows)} 行，看起来都没问题，很棒！")

    model_id = config.valid_model(model or config.CLAUDE_DEFAULT_MODEL)
    return {"lines": rows, "summary": summary, "provider": "claude:" + model_id}


def ask(message: str,
        *,
        problem: str = "",
        focus: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        render_mode: Optional[str] = None,
        allow_special: Optional[List[str]] = None,
        model: Optional[str] = None,
        session_id: str = "assistant") -> Dict[str, Any]:
    """Per-line follow-up chat. Grounds the reply in the clicked line (``focus`` =
    ``{idx, content, analysis}``) on top of the problem. Always returns 200 with a
    ``provider`` so the shared chat control can degrade gracefully when Claude is down.
    """
    if not claude_service.available():
        return {"reply": None, "provider": "unavailable", "available": False,
                "reason": "Claude gateway not configured." if not config.is_configured()
                          else "Claude temporarily unavailable (circuit breaker)."}
    try:
        system = prompts.build_assistant_chat_system(
            problem, focus=focus, render_mode=render_mode, allow_special=allow_special)
        messages = prompts.to_messages(history or [], message)
        reply = claude_service.complete(
            system=system, messages=messages, model=model, session_id=session_id)
        model_id = config.valid_model(model or config.CLAUDE_DEFAULT_MODEL)
        return {"reply": reply, "provider": "claude:" + model_id, "available": True}
    except ClaudeError as e:
        return {"reply": None, "provider": "error", "available": False, "reason": str(e)}
