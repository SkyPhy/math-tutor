"""Offline check for the SymPy compute-tool sandbox (sympy_compute.py) — the
calculator the AI calls mid-answer via <sympy>…</sympy>. This is COMPUTE, not
grading (SymPy stays retired from judging; see reasoner.py / test_reasoner_offline).

    py -3.12 test_sympy_compute_offline.py     # from anywhere; exits non-zero on failure

No gateway / .env needed: exercises only the pure evaluator + tag machinery
(find_requests / build_feedback / strip_tags), never claude_service. Plain asserts,
no pytest dependency (project keeps a zero-extra-deps rule).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # put backend/ on path
from app import sympy_compute as sc

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


print("=== _compute_one: exact maths → LaTeX ===")
CASES = [
    # (source, expected-ok, expected-latex-or-None)
    ("solve(x**2 - 5*x + 6, x)", True, r"\left[ 2, \  3\right]"),
    ("integrate(sin(x), (x, 0, pi))", True, "2"),
    ("diff(x^3 + 2*x, x)", True, "3 x^{2} + 2"),      # ^ accepted as power
    ("factor(x^4 - 1)", True, r"\left(x - 1\right) \left(x + 1\right) \left(x^{2} + 1\right)"),
    ("2/4 + 1/6", True, r"\frac{2}{3}"),               # exact rational, not 0.666…
    ("sqrt(50)", True, r"5 \sqrt{2}"),
    ("solve(Eq(2*x + 5, 15), x)", True, r"\left[ 5\right]"),
    ("summation(k, (k, 1, 100))", True, "5050"),
    ("limit(sin(x)/x, x, 0)", True, "1"),
]
for src, want_ok, want_tex in CASES:
    ok, payload = sc._compute_one(src)
    check(f"compute {src!r} ok", ok, want_ok)
    if want_ok and want_tex is not None:
        check(f"compute {src!r} latex", payload, want_tex)


print("\n=== _compute_one: unsafe / bad input is refused, never executed ===")
for bad in ('__import__("os")', "open('x')", "import os", "eval('1')",
            "os.system('x')", "lambda: 1", "getattr(x, 'y')"):
    ok, _ = sc._compute_one(bad)
    check(f"refuse {bad!r}", ok, False)
# A genuine parse error is a clean failure, not a crash.
check("garbage 'solve(' fails cleanly", sc._compute_one("solve(")[0], False)
check("empty fails", sc._compute_one("   ")[0], False)


print("\n=== find_requests / has_request: only <sympy>, never <sympya> ===")
txt = "先算 <sympy>factor(x^2-1)</sympy> 再 <sympy> 2**10 </sympy>，结果 <sympya>x</sympya> 忽略"
check("find two requests", sc.find_requests(txt), ["factor(x^2-1)", "2**10"])
check("has_request true", sc.has_request(txt), True)
check("result tag alone is not a request",
      sc.has_request("<sympya>\\frac12</sympya>"), False)
check("empty text no request", sc.has_request(""), False)


print("\n=== strip_tags: final reply carries no tool scaffolding ===")
check("strips both tags",
      sc.strip_tags("答案是 <sympy>solve(x,x)</sympy> 和 <sympya>0</sympya>。"),
      "答案是  和 。")
check("clean text untouched", sc.strip_tags("就是 x=2。"), "就是 x=2。")


print("\n=== build_feedback: pairs each result in <sympya>, in order ===")
fb = sc.build_feedback(["factor(x^2 - 1)", "1/2 + 1/3"])
check("feedback wraps result 1", "<sympya>\\left(x - 1\\right) \\left(x + 1\\right)</sympya>" in fb, True)
check("feedback wraps result 2 (exact 5/6)", "<sympya>\\frac{5}{6}</sympya>" in fb, True)
check("feedback echoes source 1", "`factor(x^2 - 1)`" in fb, True)
# A bad request inside a batch degrades to an error note, not a crash.
fb2 = sc.build_feedback(["solve("])
check("bad request → 错误 note", "错误：" in fb2, True)


print(f"\n================  {passed} passed, {failed} failed  ================")
sys.exit(1 if failed else 0)
