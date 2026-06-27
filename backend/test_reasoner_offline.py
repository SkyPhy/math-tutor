"""Offline regression check for the reasoner's numeric normaliser + consensus
voting — the SymPy-free correctness core of de-symbolised grading.

    py -3.12 test_reasoner_offline.py        # from anywhere; exits non-zero on failure

No gateway / .env needed: it exercises only the pure-Python comparison engine, so
it stays runnable even while the gateway secrets are blank. Plain asserts, no
pytest dependency (the project keeps a zero-extra-deps rule).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # put backend/ on path
from app.reasoner import (
    _safe_eval_number, _canonical_answer, _values_match, LLMReasoner,
)

passed = failed = 0


def check(desc, got, want):
    global passed, failed
    ok = got == want
    passed += ok
    failed += not ok
    mark = "PASS" if ok else "FAIL"
    if not ok:
        print(f"[{mark}] {desc}\n        got={got!r}  want={want!r}")
    else:
        print(f"[{mark}] {desc}")


print("=== _values_match: a student answer vs a consensus 'ground truth' ===")
# (student, reference, expected-match)
MATCH_CASES = [
    # fraction / decimal / percent equivalence
    ("1/2", "0.5", True),
    ("0.50", "1/2", True),
    ("50%", "0.5", True),
    ("3/4", "0.75", True),
    # arithmetic the student may leave unevaluated
    ("(8*7)/2", "28", True),
    ("2^3", "8", True),
    # sets, order-independent, with negatives
    ("2, 3", "3, 2", True),
    ("-3, 2", "2, -3", True),
    ("x=2, y=3", "y=3, x=2", True),          # system of equations
    # equation form on either side
    ("x = 12", "12", True),
    ("1 + 1 = 2", "2", True),
    # units / trailing words (numeric-core fallback)
    ("12", "12 apples", True),
    ("12 个苹果", "12", True),
    ("5 cm", "5", True),
    # booleans, incl. Chinese
    ("成立", "true", True),
    ("不成立", "false", True),
    ("对", "yes", True),
    # thousands separators
    ("1,000", "1000", True),
    ("12,345", "12345", True),
    # genuine non-matches (must stay False)
    ("2", "3", False),
    ("2", "2, 3", False),                     # missing a root
    ("2, 3", "2", False),                     # extra root
    ("成立", "false", False),
    ("1/3", "0.5", False),
]
for student, ref, want in MATCH_CASES:
    check(f"match({student!r}, {ref!r})", _values_match(student, ref), want)


print("\n=== _safe_eval_number: arithmetic strings to exact value ===")
def asfrac(s):
    v = _safe_eval_number(s)
    return None if v is None else (v.numerator, v.denominator)

check("'1/2'", asfrac("1/2"), (1, 2))
check("'0.5'", asfrac("0.5"), (1, 2))
check("'50%'", asfrac("50%"), (1, 2))
check("'(8*7)/2'", asfrac("(8*7)/2"), (28, 1))
check("'2^3'", asfrac("2^3"), (8, 1))
check("'1,000' (thousands)", asfrac("1,000"), (1000, 1))
check("'abc' is None", _safe_eval_number("abc"), None)
check("'1/0' is None (no crash)", _safe_eval_number("1/0"), None)


print("\n=== _canonical_answer: voting key collapse ===")
check("'2, 3' == '3, 2'", _canonical_answer("2, 3") == _canonical_answer("3, 2"), True)
check("'x=2,y=3' == 'y=3,x=2'",
      _canonical_answer("x=2, y=3") == _canonical_answer("y=3, x=2"), True)
check("'x=2,y=3' keeps BOTH values",
      _canonical_answer("x=2, y=3"), _canonical_answer("2, 3"))


print("\n=== consensus voting tally ===")
R = LLMReasoner()
def paths(*answers):
    return [{"angle": "a", "answer": a, "canonical": _canonical_answer(a),
             "steps": "", "kind": "", "confidence": 0.7} for a in answers]

c = R._consensus(paths("12", "12", "13"), 3)
check("2/3 agree -> consensus", (c["status"], c["votes"], c["answer"]),
      ("consensus", 2, "12"))
c = R._consensus(paths("12", "13", "14"), 3)
check("all disagree -> no_consensus", c["status"], "no_consensus")
c = R._consensus(paths("12", "12", "13", "13"), 4)
check("2/4 tie -> plurality", c["status"], "plurality")
c = R._consensus(paths("0.5", "1/2", "50%"), 3)
check("0.5/'1/2'/50% all agree -> consensus 3/3",
      (c["status"], c["votes"]), ("consensus", 3))

print("\n=== adversarial: the fixes must NOT over-merge or under-reject ===")
# spaced set of two large numbers must stay a 2-element set, not merge to 100200
check("'100, 200' stays a 2-set vs '100200'", _values_match("100, 200", "100200"), False)
# compact set still a set
check("'2,3' is the set {2,3}", _values_match("2,3", "3, 2"), True)
# wrong value in a system must be rejected
check("system x=2,y=4 != x=2,y=3", _values_match("x=2, y=4", "x=2, y=3"), False)
# partial system (missing a variable's value) must be rejected
check("system missing a value rejected", _values_match("x=2", "x=2, y=3"), False)
# a genuine four-digit number with no comma still equals its grouped form
check("'2500' == '2,500'", _values_match("2500", "2,500"), True)

print(f"\n================  {passed} passed, {failed} failed  ================")
sys.exit(1 if failed else 0)
