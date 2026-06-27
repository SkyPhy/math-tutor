"""
app.legacy — RETIRED implementations kept only for graceful offline fallback.
============================================================================
Code in this package is NO LONGER on the main path. It is retained as a
non-authoritative safety net for when the primary path (multi-path LLM consensus,
see `app.reasoner`) is unavailable. Nothing here is the source of truth.

Currently houses:
  - sympy_grader: the old SymPy correctness judge, demoted to an offline fallback
    for `/verify` grading (de-symbolization step 3, 2026-06-27).

The SymPy *rendering* engine (`NeuroSymbolicEngine`: latex / classification / step
generation) still lives in `app.main` because `/analyze`·`/hint`·`/animate`·`/plot`
use it for non-correctness display; migrating those is a separate, later step.
"""
