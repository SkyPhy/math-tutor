"""
sympy_grader.py — RETIRED SymPy correctness judge (offline fallback only).
==========================================================================
This was the original grading oracle. It is NO LONGER the source of truth:
`app.reasoner.reasoner_engine.grade()` (multi-path LLM consensus, validated live
2026-06-27) decides correctness on the main path. This module is invoked ONLY as
a non-authoritative cross-check when consensus is unavailable — the gateway is
down, or the independent derivations disagreed — so simple algebra stays gradable
offline (graceful degradation). See docs/DEVELOPMENT_PLAN.md §4 step 3.

A CAS only covers a sliver of the elementary curriculum (equations / simplify /
arithmetic); word problems, geometry, measurement and statistics it silently
declines. So this fallback returns a verdict ONLY where SymPy is confident, and
None ("undetermined") otherwise — the caller then declines to guess.

Self-contained on purpose: it imports nothing from `app.main` (which would be a
circular import). The solver it needs (`NeuroSymbolicEngine.solve_with_steps`) is
passed IN as a callable, so this module depends only on SymPy.
"""
from typing import Any, Callable, Dict, List, Optional

from sympy import simplify
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor,
)

_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def _safe_parse(expr_str: str):
    """Parse an expression string into a SymPy object with safety transforms.
    (A local copy of app.main.safe_parse, kept here so this module stays
    independent of main.)"""
    cleaned = expr_str.replace("^", "**").strip()
    return parse_expr(cleaned, transformations=_TRANSFORMATIONS)


def compare_answer(correct: List[str], answer: str) -> Optional[bool]:
    """Compare a student `answer` against known-correct value(s) (each a string).
    Handles boolean identities and numeric/symbolic sets. None = undetermined."""
    if not correct:
        return None

    # Identity problems whose solution is a boolean ("True"/"False").
    if len(correct) == 1 and correct[0] in ("True", "False"):
        got = answer.strip().lower().rstrip(".!。")
        truthy = {"true", "yes", "correct", "成立", "对", "正确"}
        falsy = {"false", "no", "incorrect", "不成立", "错", "错误"}
        if got in truthy:
            return correct[0] == "True"
        if got in falsy:
            return correct[0] == "False"
        return None  # can't tell what the student meant → undetermined

    # Numeric / symbolic answers: compare the SET of values the student gave
    # against the SET of correct values. Tolerate "x = 2", "2", "2, -3" forms.
    try:
        correct_vals = [_safe_parse(c) for c in correct]
    except Exception:
        return None

    raw = answer.strip()
    if "=" in raw:                       # student wrote "x = 2" → keep the value
        raw = raw.split("=")[-1].strip()
    candidates = [p.strip() for p in raw.split(",") if p.strip()]
    if not candidates:
        return None
    try:
        student_vals = [_safe_parse(c) for c in candidates]
    except Exception:
        return False                     # unparseable answer → simply wrong

    def _eq(a, b) -> bool:
        try:
            return simplify(a - b) == 0
        except Exception:
            return False

    # Correct iff every expected value is matched AND the student added no extras.
    all_covered = all(any(_eq(cv, sv) for sv in student_vals) for cv in correct_vals)
    no_extras = all(any(_eq(sv, cv) for cv in correct_vals) for sv in student_vals)
    return all_covered and no_extras


def sympy_grade(expression: str, answer: str,
                solver: Callable[[str], Dict[str, Any]]) -> Optional[bool]:
    """SymPy-only verdict: True/False where SymPy can solve & compare, else None.

    `solver` is `NeuroSymbolicEngine.solve_with_steps` (injected to avoid importing
    main). Exact and instant where SymPy is confident; None otherwise.
    """
    engine = solver(expression)
    if engine.get("verification_status") == "error":
        return None
    return compare_answer(engine.get("solution") or [], answer)
