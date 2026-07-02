"""
sympy_compute.py — SymPy as a COMPUTATION TOOL for the AI (never a judge).
==========================================================================
SymPy has been FULLY RETIRED from JUDGING (grading) — see reasoner.py. This
module gives it a different, deliberately narrow job: an on-demand CALCULATOR the
AI can call in the middle of an answer.

The contract (mirrored in the prompts):

    While reasoning, when the model needs an EXACT result it should not trust
    itself to do in its head (a messy integral, a factorisation, a big fraction
    or arithmetic), it writes the SymPy expression wrapped in

        <sympy> ... </sympy>

    The backend finds every such block, evaluates it, and feeds the results back
    on the next turn wrapped — in the SAME order — in

        <sympya> ...LaTeX... </sympya>

    so the model can locate each result precisely and keep deriving from it.

This is a TOOL loop, NOT verification. Nothing here decides whether a student is
right; it only computes what the AI explicitly asked to compute. Keeping SymPy off
the grading path (its retirement) and giving it this compute-only role are two
separate things — do not let one leak into the other.

Safety. The expression is evaluated in a locked-down namespace: a curated set of
SymPy callables/constants (plus the builders `Symbol`/`Integer`/`Float`/`Rational`/
`Function` that SymPy's own number/symbol transforms emit), NO Python builtins,
and unknown identifiers auto-become free symbols. `parse_expr` is `eval` under the
hood, so obviously-dangerous source (`__…__`, import, exec, attribute access into
os/sys, …) is refused before evaluation, and `global_dict` carries no builtins.
The input comes from our own prompted model, not the open internet.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import sympy
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, convert_xor,
)

from .claude_service import claude_service


# ── tags ─────────────────────────────────────────────────────────────────
# NOTE the `>` after `sympy` in the request pattern: it makes `<sympy>` and the
# result tag `<sympya>` distinguishable, so a result block is never mistaken for
# a new request block.
_REQUEST_RE = re.compile(r"<sympy>(.*?)</sympy>", re.S | re.I)
_RESULT_RE = re.compile(r"<sympya>(.*?)</sympya>", re.S | re.I)

# How many compute→continue round-trips we allow before forcing an end (a runaway
# guard, not a normal limit — a real answer needs one or two rounds at most).
DEFAULT_ROUNDS = 4
# Per round, cap how many blocks we evaluate so one reply can't fan out unbounded.
MAX_BLOCKS_PER_ROUND = 12


# ── the sandbox ────────────────────────────────────────────────────────────
# Builders SymPy's transforms EMIT into the code (auto_number → Integer/Float,
# auto_symbol → Symbol, undefined f(x) → Function). These must always resolve or
# even a plain `2` fails, so they are non-negotiable members of the namespace.
_CORE_BUILDERS = ("Symbol", "Integer", "Float", "Rational", "Function")

# The maths surface the AI may call inside <sympy>. Curated on purpose: anything
# not here (and not a number/symbol) simply isn't available. Names missing from
# this SymPy build are skipped when the namespace is assembled below.
_ALLOWED_NAMES = (
    # constants
    "pi", "E", "I", "oo", "zoo", "nan", "S", "GoldenRatio", "EulerGamma", "Catalan",
    # relations / logic
    "Eq", "Ne", "Lt", "Le", "Gt", "Ge", "And", "Or", "Not",
    # elementary functions
    "sqrt", "cbrt", "root", "Abs", "sign", "exp", "log", "ln", "factorial",
    "binomial", "gcd", "lcm", "Mod", "floor", "ceiling", "Max", "Min",
    # trig / hyperbolic
    "sin", "cos", "tan", "cot", "sec", "csc", "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    # algebra / simplification
    "solve", "solveset", "linsolve", "nonlinsolve", "simplify", "expand", "factor",
    "cancel", "apart", "together", "collect", "nsimplify", "radsimp", "ratsimp",
    "trigsimp", "expand_trig", "expand_log", "logcombine", "powsimp",
    "Poly", "degree", "roots", "real_roots",
    # calculus
    "diff", "integrate", "limit", "series", "summation", "Sum", "product", "Product",
    "Derivative", "Integral", "Limit",
    # sets / matrices / misc
    "Matrix", "eye", "zeros", "ones", "Interval", "FiniteSet", "Union",
    "Intersection", "re", "im", "conjugate", "arg", "N", "symbols",
)


def _build_namespace() -> Dict[str, object]:
    ns: Dict[str, object] = {}
    for name in _CORE_BUILDERS + _ALLOWED_NAMES:
        obj = getattr(sympy, name, None)
        if obj is not None:
            ns[name] = obj
    return ns


_NAMESPACE = _build_namespace()
_TRANSFORMS = standard_transformations + (convert_xor,)

# Refuse source that has no business in a maths expression BEFORE it is evaluated.
# `__…__` blocks dunder access; the rest close off imports / exec / process & fs
# reach even though auto_symbol would already shadow most of them into Symbols.
_UNSAFE = re.compile(
    r"(__|\bimport\b|\bexec\b|\beval\b|\bopen\b|\bcompile\b|\binput\b|\blambda\b"
    r"|\bos\b|\bsys\b|\bsubprocess\b|\bglobals\b|\blocals\b|\bgetattr\b"
    r"|\bsetattr\b|\bdelattr\b|\bvars\b|\bfile\b)"
)

# A single <sympy> block should be one expression; a huge one is almost certainly
# junk (or an attempt to smuggle something), so bound its length.
_MAX_SRC_LEN = 400


def _compute_one(src: str) -> Tuple[bool, str]:
    """Evaluate ONE expression string. Returns (ok, payload): on success payload is
    the LaTeX of the result; on failure it is a short, safe Chinese reason so the
    model can react (retry differently, or compute by hand) instead of stalling."""
    s = (src or "").strip()
    if not s:
        return False, "空表达式"
    if len(s) > _MAX_SRC_LEN:
        return False, "表达式过长"
    if _UNSAFE.search(s):
        return False, "表达式含不允许的内容"
    try:
        # global_dict={} carries no builtins; unknown names become free symbols.
        result = parse_expr(s, local_dict=_NAMESPACE, global_dict={},
                            transformations=_TRANSFORMS)
    except Exception as e:                       # parse / evaluation error
        return False, f"无法计算（{type(e).__name__}）"
    try:
        return True, sympy.latex(result)
    except Exception:
        return False, "结果无法转为 LaTeX"


def find_requests(text: str) -> List[str]:
    """The non-empty <sympy> expressions in a model reply, in order."""
    if not text:
        return []
    return [m.strip() for m in _REQUEST_RE.findall(text) if m.strip()]


def has_request(text: str) -> bool:
    return bool(find_requests(text))


def strip_tags(text: str) -> str:
    """Remove any <sympy>/<sympya> machinery from a string — used on the FINAL
    reply so the student never sees the tool scaffolding (the model is told to
    drop them itself; this is the defensive backstop)."""
    if not text:
        return text
    text = _REQUEST_RE.sub("", text)
    text = _RESULT_RE.sub("", text)
    return text.strip()


def build_feedback(requests: List[str]) -> str:
    """Compute each requested expression and phrase the results as the next user
    turn — each result wrapped in <sympya> and paired with its source so the model
    can locate it exactly."""
    lines = ["[SymPy 运算结果] 你上一条中的 <sympy> 请求已由后端 SymPy 计算，"
             "按顺序对应如下（结果为 LaTeX，包在 <sympya> 内）："]
    for i, src in enumerate(requests[:MAX_BLOCKS_PER_ROUND], 1):
        ok, payload = _compute_one(src)
        inner = payload if ok else f"错误：{payload}"
        lines.append(f"{i}. 输入 `{src}` ⟶ <sympya>{inner}</sympya>")
    if len(requests) > MAX_BLOCKS_PER_ROUND:
        lines.append(f"（本轮仅计算前 {MAX_BLOCKS_PER_ROUND} 个请求，其余请下一轮再提交）")
    lines.append("请据此继续推导。如需更多计算就再写 <sympy>…</sympy>；否则给出最终解答，"
                 "并且最终回复里不要保留任何 <sympy> 或 <sympya> 标签。")
    return "\n".join(lines)


def complete_with_compute(
    *,
    system: str,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    session_id: str = "anon",
    max_rounds: int = DEFAULT_ROUNDS,
    **complete_kwargs,
) -> str:
    """Run a normal chat completion, but service any <sympy> compute requests the
    model emits and let it continue from the results.

    Same signature surface as ``claude_service.complete`` (extra kwargs like
    ``max_tokens`` / ``temperature`` pass straight through), so call sites swap one
    for the other. Raises ``ClaudeError`` exactly as ``complete`` does — callers keep
    their existing fallback. The returned text is the final reply with all tool tags
    stripped; when no <sympy> block is ever emitted this is just a single call.
    """
    convo = list(messages or [])
    reply = ""
    for round_i in range(max_rounds + 1):
        reply = claude_service.complete(
            system=system, messages=convo, model=model,
            session_id=session_id, **complete_kwargs,
        )
        requests = find_requests(reply)
        if not requests or round_i == max_rounds:
            break
        # Keep the model's own request text in context (unstripped), then answer it.
        convo = convo + [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": build_feedback(requests)},
        ]
    return strip_tags(reply)
