"""
reasoner.py — Multi-path LLM reasoning with consensus.
=======================================================
This module is the replacement for SymPy as the SOURCE OF TRUTH for correctness.

The old iron rule — "SymPy is the only source of truth; the AI never computes its
own answer" — was deleted as wrong. A CAS cannot reach most of the elementary
curriculum (word problems, geometry, measurement, statistics, plain reasoning),
so it silently declines exactly the problems students actually bring, and the
tutor could never tell them whether their answer was right.

The new stance is VERIFICATION BY CONSENSUS, not by CAS:

    Ask the model to solve the same problem several times, INDEPENDENTLY and via
    deliberately different angles, then keep the answer the independent
    derivations AGREE on. Agreement across independent paths is the confidence
    signal — a lone path is never trusted. Self-consistency replaces the symbolic
    oracle.

No SymPy is used here, by design. Answer comparison is done with a small,
self-contained numeric normaliser (Python `fractions` + a safe `ast` arithmetic
evaluator), so "1/2", "0.5", " 0.50 " and "1 / 2" all collapse to one canonical
value without any external CAS.

When a question already carries a KNOWN-correct answer (the bank's stored answer —
which also holds 学科网-fetched answers — or a prior consensus), grading does NOT
re-solve: `grade_with_reference()` compares the student's answer to that answer
directly, first with the SymPy-free numeric normaliser below (works offline) and,
if that does not settle it, with a single LLM equivalence judge. SymPy has fully
retired from judging (2026-07-02): there is no CAS anywhere on the grading path.

Everything degrades gracefully: if the gateway is unavailable and the numeric
normaliser cannot settle a comparison, the reasoner returns an "undetermined"
verdict (correct=None) and the caller declines to guess rather than reaching for
a CAS.
"""

import ast
import json as _json
import re as _re
from fractions import Fraction
from typing import Any, Dict, List, Optional, Set

from . import prompts
from .claude_service import claude_service, ClaudeError


# ═══════════════════════════════════════════════════════════════════════
#  SELF-CONTAINED NUMERIC NORMALISER  (no SymPy — that is the whole point)
# ═══════════════════════════════════════════════════════════════════════

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)


def _eval_ast(node: ast.AST) -> Fraction:
    """Evaluate a tiny arithmetic AST to an exact Fraction. Raises on anything
    outside { + - * / ** , parens, numeric literals } so it is safe to run on
    model-supplied strings."""
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):           # bool is an int subclass — reject
            raise ValueError("boolean literal")
        if isinstance(node.value, int):
            return Fraction(node.value)
        if isinstance(node.value, float):
            # Collapse float noise: 0.5 -> 1/2, 0.333333 -> 333333/1000000 (close enough).
            return Fraction(node.value).limit_denominator(10 ** 9)
        raise ValueError("non-numeric constant")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY):
        v = _eval_ast(node.operand)
        return v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        left, right = _eval_ast(node.left), _eval_ast(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ZeroDivisionError
            return left / right
        # Pow: keep it rational — integer exponent within a sane bound only.
        if right.denominator != 1 or abs(right) > 64:
            raise ValueError("unsupported exponent")
        return left ** int(right)
    raise ValueError("unsupported expression")


# A comma is BOTH a set separator ("2, 3" = two roots) and a thousands grouping
# ("1,000" = one number). Disambiguate by the universal grouping shape: a comma
# wedged between digits and followed by EXACTLY three more digits is a separator
# inside one number, so strip it. "2, 3" (space, 1-digit group) and "2,3" (1-digit
# group) are left intact as sets. The only sacrifice is the space-less compact set
# "100,200" — read as 100200 — but real set answers use ", " with a space.
_THOUSANDS = _re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


def _strip_thousands(s: str) -> str:
    return _THOUSANDS.sub("", s)


def _safe_eval_number(text: Any) -> Optional[Fraction]:
    """Evaluate a numeric/arithmetic string to an exact Fraction, or None if it is
    not a pure number. Handles fractions, decimals, %, thousands commas, unicode × ÷."""
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    s = (s.replace("^", "**").replace("×", "*").replace("÷", "/")
          .replace("−", "-").replace(" ", ""))
    s = _strip_thousands(s)
    percent = s.endswith("%")
    if percent:
        s = s[:-1]
    if not s:
        return None
    try:
        val = _eval_ast(ast.parse(s, mode="eval"))
    except Exception:
        return None
    return val / 100 if percent else val


_TRUE_WORDS = {"true", "yes", "correct", "t", "y", "成立", "对", "正确", "是", "真"}
_FALSE_WORDS = {"false", "no", "incorrect", "f", "n", "不成立", "错", "错误", "否", "假"}

_NUM_TOKEN = _re.compile(r"-?\d+(?:\.\d+)?(?:/\d+)?")
_SPLIT_SET = _re.compile(r"[,，;；、]")


def _canonical_piece(piece: str) -> str:
    """Canonicalise ONE answer token for voting: booleans, exact numbers, or
    whitespace-collapsed text. A leading "var =" is dropped per-piece so each
    member of a system ("x = 2", "y = 3") keeps its own value."""
    p = piece.strip()
    if "=" in p:                       # "x = 2" → "2"; "1 + 1 = 2" → "2"
        p = p.split("=")[-1].strip()
    p = p.lower().rstrip(".!。！?？ ").strip()
    if not p:
        return ""
    if p in _TRUE_WORDS:
        return "bool:true"
    if p in _FALSE_WORDS:
        return "bool:false"
    num = _safe_eval_number(p)
    if num is not None:
        return f"num:{num.numerator}/{num.denominator}"
    return "txt:" + " ".join(p.split())


def _canonical_answer(ans: Any) -> str:
    """Collapse a whole answer string into a canonical key. Order-independent for
    sets, so "2, -3" and "-3, 2" match. Empty string ⇒ uncanonicalisable."""
    if ans is None:
        return ""
    raw = _strip_thousands(str(ans).strip())   # "1,000" → "1000" before set-split
    # NOTE: "=" is handled per-piece (see _canonical_piece) so a system answer
    # "x=2, y=3" keeps BOTH values instead of collapsing to the last one.
    parts = [p for p in _SPLIT_SET.split(raw) if p.strip()] or [raw]
    canon = sorted({c for c in (_canonical_piece(p) for p in parts) if c})
    return "|".join(canon)


def _numbers_in(s: Any) -> Set[Fraction]:
    """Exact set of numeric values appearing in a string. Lets "12" match
    "12 apples" / "12 个" when canonical text comparison would miss it."""
    out: Set[Fraction] = set()
    for tok in _NUM_TOKEN.findall(_strip_thousands(str(s))):
        v = _safe_eval_number(tok)
        if v is not None:
            out.add(v)
    return out


def _values_match(student: Any, reference: Any) -> bool:
    """Robust equality between a student answer and the consensus answer."""
    cs, cr = _canonical_answer(student), _canonical_answer(reference)
    if cs and cs == cr:
        return True
    # Numeric-core fallback: same set of numbers (handles units / trailing words).
    ns, nr = _numbers_in(student), _numbers_in(reference)
    return bool(ns) and ns == nr


# ═══════════════════════════════════════════════════════════════════════
#  JSON EXTRACTION  (tolerate fences / surrounding prose)
# ═══════════════════════════════════════════════════════════════════════

def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    t = _re.sub(r"```$", "", _re.sub(r"^```(?:json)?", "", text.strip()).strip()).strip()
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        t = t[start:end + 1]
    try:
        obj = _json.loads(t)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _coerce_confidence(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, f))


# ═══════════════════════════════════════════════════════════════════════
#  THE REASONER
# ═══════════════════════════════════════════════════════════════════════

# Distinct angles keep the paths genuinely independent — agreement only means
# something if the paths did not all walk the identical road. Temperatures rise
# across paths to widen the search a little.
_ANGLES = [
    "Solve it directly and carefully, step by step.",
    "Solve it using a different method than the most obvious one, then re-check "
    "your result by estimation or by substituting it back.",
    "Read slowly: restate exactly what is asked, solve it, and confirm the answer "
    "satisfies every condition before reporting it.",
    "Treat it as checking another student's work — derive the answer yourself and "
    "verify it independently.",
]
_TEMPS = [0.2, 0.6, 0.9, 0.45]


class LLMReasoner:
    """Solve / grade by independent multi-path consensus. SymPy-free."""

    DEFAULT_PATHS = 3

    # ── status ──────────────────────────────────────────────────────────
    def available(self) -> bool:
        return claude_service.available()

    # ── solve: run N independent paths, return the consensus ────────────
    def solve(
        self,
        problem: str,
        n_paths: Optional[int] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a consensus result:
        {status, answer, answer_canonical, agreement, votes, total_paths,
         requested_paths, paths[], winner_steps}.

        status ∈ {consensus, plurality, no_consensus, no_paths, unavailable}.
        """
        requested = n_paths or self.DEFAULT_PATHS
        n = max(1, min(int(requested), len(_ANGLES)))

        if not claude_service.available():
            return self._empty("unavailable", requested)

        paths: List[Dict[str, Any]] = []
        for i in range(n):
            system = prompts.build_solve_prompt(problem, _ANGLES[i])
            user = (f"Problem: {problem}\n"
                    "Solve it now and return only the JSON object.")
            try:
                text = claude_service.complete(
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    model=model,
                    session_id=session_id or "reason",
                    max_tokens=600,
                    temperature=_TEMPS[i],
                )
            except ClaudeError:
                continue
            obj = _parse_json_object(text)
            if not obj:
                continue
            ans = obj.get("final_answer")
            if ans is None or not str(ans).strip():
                continue
            paths.append({
                "angle": _ANGLES[i],
                "answer": str(ans).strip(),
                "canonical": _canonical_answer(ans),
                "steps": str(obj.get("steps", ""))[:500],
                "kind": str(obj.get("answer_kind", "")),
                "confidence": _coerce_confidence(obj.get("confidence")),
            })

        return self._consensus(paths, requested)

    def _empty(self, status: str, requested: int) -> Dict[str, Any]:
        return {
            "status": status, "answer": None, "answer_canonical": "",
            "agreement": 0.0, "votes": 0, "total_paths": 0,
            "requested_paths": requested, "paths": [], "winner_steps": "",
        }

    def _consensus(self, paths: List[Dict[str, Any]], requested: int) -> Dict[str, Any]:
        if not paths:
            return self._empty("no_paths", requested)

        # Tally votes by canonical answer (fall back to lowercased raw if a path
        # produced an uncanonicalisable answer, so it still votes for itself).
        tally: Dict[str, List[Dict[str, Any]]] = {}
        for p in paths:
            key = p["canonical"] or ("raw:" + p["answer"].lower())
            tally.setdefault(key, []).append(p)

        # Winner: most votes, tie-broken by summed confidence.
        winner_key = max(
            tally, key=lambda k: (len(tally[k]), sum(x["confidence"] for x in tally[k]))
        )
        group = tally[winner_key]
        votes = len(group)
        total = len(paths)
        agreement = votes / total
        rep = max(group, key=lambda x: x["confidence"])  # representative answer

        if votes >= 2 and votes > total / 2:
            status = "consensus"        # clear majority of the paths that answered
        elif votes >= 2:
            status = "plurality"        # agreed, but only a plurality (e.g. 2/4 split)
        else:
            status = "no_consensus"     # every path disagreed — not trustworthy

        return {
            "status": status,
            "answer": rep["answer"],
            "answer_canonical": winner_key,
            "agreement": round(agreement, 3),
            "votes": votes,
            "total_paths": total,
            "requested_paths": requested,
            "paths": [
                {k: p[k] for k in ("angle", "answer", "kind", "confidence")}
                for p in paths
            ],
            "winner_steps": rep["steps"],
        }

    # ── grade: solve for the truth, then compare the student's answer ───
    def grade(
        self,
        problem: str,
        student_answer: str,
        n_paths: Optional[int] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Grade by consensus. Returns:
        {correct: Optional[bool], judged_by, reason, agreement?, ground_truth?,
         votes_label?, consensus}.

        correct=None means undetermined (gateway down, or paths disagreed) — the
        caller should fall back rather than guess.
        """
        sol = self.solve(problem, n_paths=n_paths, model=model, session_id=session_id)

        if sol["status"] in ("unavailable", "no_paths"):
            return {"correct": None, "judged_by": None, "reason": None,
                    "consensus": sol}

        if sol["status"] == "no_consensus" or not sol.get("answer"):
            # Independent derivations disagreed → not confident enough to grade.
            return {"correct": None, "judged_by": "consensus",
                    "reason": "多条独立推导未达成一致，暂不判定对错。",
                    "consensus": sol}

        correct = _values_match(student_answer, sol["answer"])
        votes_label = f"consensus({sol['votes']}/{sol['total_paths']})"
        if correct:
            # Only a correct submission may see the answer (it is revealed then).
            reason = f"答案正确。多条独立推导一致得到 {sol['answer']}。"
        else:
            # Do NOT leak the agreed answer on a miss — it stays backend-only until
            # the student gets it right.
            reason = "答案与标准答案不一致，请再检查。"

        return {
            "correct": bool(correct),
            "judged_by": "consensus",
            "votes_label": votes_label,
            "agreement": sol["agreement"],
            "ground_truth": sol["answer"],
            "reason": reason,
            "consensus": sol,
        }

    # ── judge against a KNOWN-correct reference answer (SymPy-free) ──────
    def match(self, reference: Any, student_answer: Any) -> bool:
        """Deterministic, SymPy-free equality between a student answer and a
        KNOWN reference answer (the numeric/canonical normaliser). Works offline;
        used as the fast path before any model call."""
        return _values_match(student_answer, reference)

    def judge_against_reference(
        self,
        problem: str,
        reference: str,
        student_answer: str,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[bool]:
        """Ask the model whether the student's answer is mathematically equivalent
        to a KNOWN-correct reference answer. SymPy-free. Returns True/False, or
        None when the gateway is down or the reply is unparseable."""
        if not claude_service.available():
            return None
        system = prompts.build_answer_judge_prompt(problem, reference)
        user = (f"学生的作答：{student_answer}\n"
                "请判断是否正确，只输出 JSON 对象。")
        try:
            text = claude_service.complete(
                system=system,
                messages=[{"role": "user", "content": user}],
                model=model,
                session_id=session_id or "judge",
                max_tokens=200,
                temperature=0.0,
            )
        except ClaudeError:
            return None
        obj = _parse_json_object(text)
        if not obj or "correct" not in obj:
            return None
        val = obj.get("correct")
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if s in ("true", "1", "yes", "correct", "对", "正确"):
            return True
        if s in ("false", "0", "no", "incorrect", "错", "错误"):
            return False
        return None

    def grade_with_reference(
        self,
        problem: str,
        reference: str,
        student_answer: str,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Grade a student's answer against a KNOWN-correct reference answer (the
        bank's stored answer / 学科网 answer / a prior consensus) — the primary
        grading path, with NO SymPy. Numeric/canonical match first (offline-capable);
        if that does not match, one LLM equivalence judge decides.

        Returns {correct: Optional[bool], judged_by, reason, ground_truth?}.
        `ground_truth` (the answer itself) is included ONLY when correct, so the
        answer is never leaked on a miss."""
        ref = (reference or "").strip()
        if not ref:
            return {"correct": None, "judged_by": None, "reason": None}

        # Fast, offline-capable path: exact numeric/canonical equality.
        if self.match(ref, student_answer):
            return {"correct": True, "judged_by": "answer-key",
                    "reason": "答案正确。", "ground_truth": ref}

        # Not a literal match — could still be equivalent (different form / units /
        # π & decimals). Let the model judge equivalence against the known answer.
        verdict = self.judge_against_reference(
            problem, ref, student_answer, model=model, session_id=session_id)
        if verdict is None:
            # Gateway down and no deterministic match → decline to guess.
            return {"correct": None, "judged_by": "answer-key",
                    "reason": "暂时无法判定，请稍后再试。"}
        if verdict:
            return {"correct": True, "judged_by": "answer-key",
                    "reason": "答案正确。", "ground_truth": ref}
        return {"correct": False, "judged_by": "answer-key",
                "reason": "答案与标准答案不一致，请再检查。"}


# Singleton used across the app.
reasoner_engine = LLMReasoner()
