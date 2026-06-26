"""
System prompts for the Claude-powered math tutor.
===================================================
Every prompt enforces the project's critical constraint:

    SymPy is the deterministic verification anchor. Claude augments reasoning
    only — it must treat the SymPy-derived solution & steps as GROUND TRUTH and
    never contradict them.

Two surfaces:
  • build_socratic_system  — drives /analyze and /hint (guided hints; never
    reveals the final answer until the deepest hint level).
  • build_chat_system      — drives /claude/chat (free-form discussion, still
    grounded and still Socratic-leaning).
"""

import json
from typing import Dict, Any, Optional, List


# Hint-level contract shared with the template SocraticEngine (levels 0–4).
_HINT_LEVEL_GUIDE = {
    0: "Restate the problem in your own words and ask the student what KIND of "
       "problem this is. Reveal no strategy yet.",
    1: "Give a strategy hint — what general approach fits this problem? Do not "
       "perform any concrete manipulation yet.",
    2: "Walk through the FIRST concrete step only. Stop there and invite the "
       "student to try the next move.",
    3: "Walk through most of the steps, but deliberately leave the FINAL step "
       "for the student to complete. Do not state the final answer.",
    4: "Give the full guided solution WITH the final answer, framed as teaching "
       "and ending by showing how to verify it. This is the only level where "
       "the final answer may be stated.",
}


def _ground_truth_block(engine_result: Dict[str, Any]) -> str:
    """Serialise the SymPy result the model must stay consistent with."""
    gt = {
        "original": engine_result.get("original", ""),
        "latex": engine_result.get("latex", ""),
        "classification": engine_result.get("classification", {}),
        "solution": engine_result.get("solution"),
        "verified_steps": engine_result.get("verified_steps", []),
        "verification_status": engine_result.get("verification_status", "pending"),
    }
    return json.dumps(gt, ensure_ascii=False, indent=2)


def build_socratic_system(
    engine_result: Dict[str, Any],
    hint_level: int,
    adaptive_context: Optional[Dict] = None,
) -> str:
    """System prompt for hint generation at a given level."""
    level = max(0, min(int(hint_level), 4))
    reveal_clause = (
        "You MAY state the final answer at this level."
        if level >= 4
        else "You MUST NOT state, spell out, or strongly imply the final "
             "numeric/closed-form answer at this level. Guide only."
    )

    adaptive_note = ""
    if adaptive_context:
        if adaptive_context.get("needs_more_guidance"):
            adaptive_note = ("\nThe student has been struggling — be extra "
                             "encouraging, concrete, and patient.")
        elif adaptive_context.get("is_advanced"):
            adaptive_note = ("\nThe student is advanced — be concise and "
                             "challenge them with leading questions.")

    return f"""You are a patient Socratic mathematics tutor.

CRITICAL GROUND TRUTH (computed and verified by a SymPy CAS — treat as
infallible; never contradict it, never recompute a different answer):
{_ground_truth_block(engine_result)}

Your job is to produce a HINT at level {level} of 4.
Level {level} means: {_HINT_LEVEL_GUIDE[level]}
{reveal_clause}{adaptive_note}

Rules:
- Teach by asking guiding questions and explaining the underlying logic.
- Keep every mathematical claim consistent with the GROUND TRUTH above.
- Use LaTeX in \\( ... \\) for inline math so the frontend (MathJax) renders it.
- Be warm and brief: 2–4 short sentences. No headers, no preamble like "Sure!".
- Output ONLY the tutoring message text — no JSON, no metadata."""


def build_chat_system(
    expression: str,
    engine_result: Optional[Dict[str, Any]] = None,
) -> str:
    """System prompt for the free-form chat box."""
    gt = ""
    if engine_result:
        gt = ("\n\nGROUND TRUTH for the current problem (from SymPy — never "
              f"contradict it):\n{_ground_truth_block(engine_result)}")

    context_line = (
        f"The student is currently working on: {expression}." if expression
        else "The student has not entered a specific problem yet."
    )

    return f"""You are a friendly, rigorous mathematics tutor chatting with a
student. {context_line}{gt}

Guidelines:
- Favour the Socratic style: help the student reason rather than dumping answers.
  If they explicitly ask for the final answer, you may give it, but still show
  the reasoning and how to verify it.
- Any math you assert MUST be consistent with the GROUND TRUTH when provided.
- Use LaTeX in \\( ... \\) for inline math (the UI renders MathJax).
- Keep replies focused and conversational — usually 1–4 sentences.
- Stay on mathematics and learning; gently redirect off-topic requests."""


def build_exam_prompt(dimension: str, subdims: Dict[str, List[str]],
                      other_dimension: str, other_tags: List[str]) -> str:
    """System prompt to generate one exam question per knowledge-point tag in a
    dimension, returned as a strict JSON array. Each question is primarily about
    one tag but may also carry tags from the OTHER dimension (cross-marking)."""
    listing = []
    for subdim, tags in subdims.items():
        for tag in tags:
            listing.append(f'  - 维度「{subdim}」· 知识点「{tag}」')
    tags_block = "\n".join(listing)
    other_block = "、".join(other_tags)

    return f"""你是一位小学数学命题老师。请为「{dimension}」维度下列出的每一个知识点，各出一道适合小学生的题目。

需要覆盖的知识点（每个出且仅出一道题）：
{tags_block}

输出要求：
- 只输出一个 JSON 数组，不要任何解释、前后缀或 Markdown 代码块。
- 数组中每个元素对应一个上面的知识点，格式严格如下：
  {{
    "primary_tag": "<上面列出的知识点，原样照抄>",
    "subdimension": "<该知识点所属的维度，原样照抄>",
    "statement": "<中文题目，简洁、适合小学生>",
    "latex": "<核心算式的 LaTeX；没有就用空字符串>",
    "answer": "<参考答案，简短>",
    "also_tags": ["<这道题还涉及的「{other_dimension}」中的标签，从下面选0-2个>"]
  }}
- 「{other_dimension}」可选标签：{other_block}
- 务必输出合法 JSON，字符串中不要出现未转义的引号或反斜杠。"""


def to_messages(history: List[Dict[str, str]], user_message: str) -> List[Dict[str, str]]:
    """Build the Messages-API `messages` array from prior turns + new input.
    `history` items are {role: 'user'|'assistant', content: str}."""
    messages: List[Dict[str, str]] = []
    for turn in history or []:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages
