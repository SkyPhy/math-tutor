"""
Self-Evolving AI Math Tutor — Backend
======================================
Architecture layers (per the Evolving AI Math blueprint):
  1. Frontend Interface Layer  →  React + P5.js canvas
  2. Orchestration & Logic Layer  →  FastAPI endpoints (this file)
  3. Cognitive Processing Layer  →  SymPy CAS + Blending Instructions
  4. Execution & Validation Layer  →  Neuro-symbolic verification sandbox

Key subsystems implemented:
  • Socratic Engine  — guided hints, NEVER reveals final answer directly
  • Neuro-Symbolic Integration  — SymPy CAS for deterministic verification
  • Policy Engine (SEPGA)  — pedagogical guardrails, input validation
  • Experience Memory  — session history for adaptive hint generation
  • Blending Instructions  — context-aware prompt construction
  • Data Manager  — architecture metadata as JSON tree
  • ALMAS Pipeline  — Sprint → Control → Developer → Peer review stages
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sympy import (
    sympify, solve, Eq, simplify, latex, factor, expand,
    diff, integrate, Symbol, symbols, degree, Poly,
    sin, cos, tan, log, exp, sqrt, oo, lambdify,
    SympifyError
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)
from PIL import Image
from datetime import datetime
from uuid import uuid4
import io
import json
import random
import uvicorn
import traceback
import os
import html as html_lib
import urllib.request
import urllib.parse
from . import recognize  # nex-n2-pro vision handwriting recognition (recognize.py)

# ── Claude integration (Anthropic-compatible gateway) ──────────────────────
# These power the AI tutor. If the gateway is not configured (.env absent),
# claude_service.available() is False and every call site falls back to the
# deterministic template SocraticEngine, so the demo always works.
from . import config
from . import prompts
from .claude_service import claude_service, ClaudeError

# Multi-path LLM consensus reasoner — the SOURCE OF TRUTH for correctness,
# replacing SymPy. Several independent derivations must AGREE before a verdict is
# trusted (see reasoner.py). SymPy is kept only as a non-authoritative cross-check
# and an offline fallback, never as the sole arbiter.
from .reasoner import reasoner_engine

# RETIRED SymPy correctness judge — demoted to a non-authoritative OFFLINE FALLBACK
# (de-symbolization step 3, 2026-06-27). It is invoked only when consensus is
# unavailable; the rendering engine (NeuroSymbolicEngine) stays in this module.
from .legacy import sympy_grader

# User accounts & sessions, backed by SQLite (auth.py / users.db).
from . import auth

# Exam question bank — AI-generated questions tagged across two dimensions,
# stored in SQLite with tag-indexed lookup (exam.py / exams.db).
from . import exam

# Dynamic tag store — the evolving tag vocabulary in its OWN database
# (tags.py / tags.db). AI may add fitting tags and any tag may be removed;
# exam.py's hard-coded catalogues are only the initial seed.
from . import tags

# Logic-flaw diagnosis (diagnosis.py / diagnosis.db) — per-student weak logic
# types (from /verify grading) + AI-self consensus-divergence signals. Drives
# adaptive "出题 by weak logic-type" (v2.0 goals 5/6).
from . import diagnosis

# Durable experience memory — persisted to SQLite (memory.py / memory.db) so the
# tutor's adaptive context survives restarts and is shared across sessions.
from . import memory as memory_store
from .memory import memory

# Personal workspace — student draft / answer library (workspace.py / workspace.db).
# Backs the 校对屏 「存草稿 / 提交」 affordances: a corrected piece of writing is named
# and stashed per question so the student can stop and resume ("断点续作").
from . import workspace

# AI assistant — line-by-line analysis orchestration (assistant.py). Backs the ④ AI
# 助手屏: aligns "student work | AI analysis" line by line (blank where a step is fine)
# and answers per-line follow-ups. Pure logic; the /assistant/* routes below delegate
# to it (same split as workspace.py).
from . import assistant

# Manim renderer — real MP4 via Manim CE when installed, else a browser storyboard
# (manim_render.py). Backs POST /manim/render + the <manim> blocks the assistant emits.
from . import manim_render

import json as _json
import re as _re

# ═══════════════════════════════════════════════════════════════════════
#  APPLICATION BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Self-Evolving AI Math Tutor",
    description="Neuro-symbolic math tutoring with Socratic pedagogy and policy governance",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve rendered Manim clips (v0.4.5b). /manim/render writes MP4s into
# manim_render.MEDIA_DIR; this mount exposes them at /manim-media/<file>.mp4.
app.mount(manim_render.MEDIA_URL, StaticFiles(directory=manim_render.MEDIA_DIR),
          name="manim-media")


@app.on_event("startup")
def _warmup_ocr() -> None:
    """
    OCR is now a remote API (nex-n2-pro) — there is no local model to preload.
    We just log whether the OCR gateway is configured so a missing .env is
    obvious at startup rather than silently falling back to the mock.
    """
    if recognize.is_available():
        print("[startup] OCR gateway (nex-n2-pro) configured.")
    else:
        print("[startup] OCR gateway NOT configured — /recognize will return the "
              "mock expression. Set NEX_OCR_BASE_URL / NEX_OCR_API_KEY in .env.")
    # Make sure the user/session tables exist (SQLite, created on first run).
    auth.init_db()
    print(f"[startup] User DB ready ({auth.user_count()} accounts).")
    # Exam question bank tables.
    exam.init_db()
    print(f"[startup] Exam bank ready ({exam.bank_size()} questions).")
    # Dynamic tag vocabulary (own DB). Seed from exam.py's catalogues on first
    # run only — never re-seed, so AI/user adds and deletes survive restarts.
    tags.init_db()
    seeded = tags.seed_from_catalogues()
    adv = tags.seed_advanced_knowledge()   # ensure K-12+ domains exist (idempotent)
    print(f"[startup] Tag store ready ({tags.count()} active tags"
          + (f", seeded {seeded}" if seeded else "")
          + (f", +{adv} advanced" if adv else "") + ").")
    # Logic-flaw diagnosis tables (student outcomes + AI-self consensus signals).
    diagnosis.init_db()
    print("[startup] Diagnosis DB ready.")
    # Durable experience-memory tables (persists adaptive context across restarts).
    memory_store.init_db()
    print("[startup] Experience memory DB ready.")
    # Personal draft/answer library (校对屏 存草稿 / 提交; 断点续作).
    workspace.init_db()
    print(f"[startup] Workspace DB ready ({workspace.count()} drafts).")


# ═══════════════════════════════════════════════════════════════════════
#  AUTH HELPERS / DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════

def _bearer_token(authorization: Optional[str]) -> str:
    """Pull the token out of an `Authorization: Bearer <token>` header."""
    if not authorization:
        return ""
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def require_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """FastAPI dependency: reject the request (401) unless it carries a valid,
    unexpired session token. Use as `dependencies=[Depends(require_user)]` to
    protect an endpoint, or as a param to read the current user."""
    user = auth.get_user_by_token(_bearer_token(authorization))
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[Dict[str, Any]]:
    """Like require_user but returns None instead of raising when not signed in."""
    return auth.get_user_by_token(_bearer_token(authorization))


# ═══════════════════════════════════════════════════════════════════════
#  PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════

class MathRequest(BaseModel):
    expression: str
    action: str = "solve"
    session_id: Optional[str] = None
    model: Optional[str] = None   # Claude model id for the dropdown; None → default
    answer: Optional[str] = None  # student's own answer, for /verify grading (None → just solve)
    question_id: Optional[str] = None  # bank question id → grade feeds logic-flaw diagnosis

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    expression: Optional[str] = None        # the problem being discussed (for grounding)
    model: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None  # [{role:'user'|'assistant', content}]
    allow_special: Optional[List[str]] = None  # special symbols/regex/escapes the chat may use

# ── Workspace (personal draft library) request body ──
class WorkSaveRequest(BaseModel):
    session_id: Optional[str] = None       # anonymous owner when not signed in
    question_id: Optional[str] = None      # the problem this draft belongs to
    filename: Optional[str] = None         # student-chosen name
    content_md: str = ""                   # the corrected writing (markdown / latex)
    render_mode: Optional[str] = None      # '1' full-render | '2' source | '3' plain
    status: str = "tmp"                    # 'tmp' (存草稿) | 'final' (提交)
    draft_id: Optional[str] = None         # update an existing draft in place if given

# ── AI assistant (④ 助手屏) request bodies ──
class AssistantAnalyzeRequest(BaseModel):
    session_id: Optional[str] = None
    question_id: Optional[str] = None      # resolve the problem text from the bank if given
    problem: Optional[str] = None          # …or pass the problem text directly (frontend does)
    student_work_md: str = ""              # the corrected work from the 校对屏 (markdown / latex)
    render_mode: Optional[str] = None      # how that work was rendered ('1'|'2'|'3') — a reading hint
    model: Optional[str] = None

class AssistantAskRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    question_id: Optional[str] = None
    problem: Optional[str] = None
    model: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None      # prior turns [{role, content}]
    focus: Optional[Dict[str, Any]] = None              # the clicked line {idx, content, analysis}
    render_mode: Optional[str] = None
    allow_special: Optional[List[str]] = None           # special symbols the chat control can render

# ── Manim render (v0.4.5b) request body ──
class ManimRenderRequest(BaseModel):
    expression: Optional[str] = None       # the math to animate (drives the storyboard fallback)
    spec: Optional[str] = None             # natural-language <manim> note (what the clip should show)
    manim_code: Optional[str] = None       # pre-generated Manim code to render as-is (skips AI gen)
    session_id: Optional[str] = None
    model: Optional[str] = None

# ── Auth request bodies ──
class SignUpRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class SignInRequest(BaseModel):
    username: str
    password: str

class SocraticMessage(BaseModel):
    role: str  # "user" | "tutor" | "system"
    content: str
    hint_level: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class ConversationRequest(BaseModel):
    session_id: str
    message: str
    expression: Optional[str] = None

class PolicyCheckResult(BaseModel):
    allowed: bool
    violations: List[str] = []
    penalty_score: float = 0.0

class ArchitectureNode(BaseModel):
    id: str
    name: str
    type: str  # "layer" | "module" | "component"
    purpose: str
    children: List["ArchitectureNode"] = []
    status: str = "active"

ArchitectureNode.model_rebuild()

# ═══════════════════════════════════════════════════════════════════════
#  EXPERIENCE MEMORY — Persistent session learning
# ═══════════════════════════════════════════════════════════════════════

# ExperienceMemory now lives in memory.py as `PersistentExperienceMemory`,
# backed by SQLite (memory.db) so adaptive context survives restarts. The
# singleton `memory` is imported at the top of this file; its method surface
# (get_or_create_session / record_interaction / add_message / get_conversation
# / get_adaptive_context) is unchanged, so the call sites below are untouched.

# ═══════════════════════════════════════════════════════════════════════
#  POLICY ENGINE (SEPGA) — Compliance-by-Design
# ═══════════════════════════════════════════════════════════════════════

class PolicyEngine:
    """
    Implements the SEPGA (Self-Evolving, Policy-Governed Agentic Automation)
    framework. Acts as a Constrained Markov Decision Process that evaluates
    proposed actions and assigns penalty scores to violations.

    Pedagogical guardrails enforce the Socratic constraint:
      "You are a tutor. Break the problem down into steps, explain the
       underlying logic, and never output the final answer immediately."
    """

    # Immutable policy rules
    POLICIES = {
        "socratic_constraint": {
            "description": "Never output the final answer directly",
            "penalty": 10.0,
            "type": "pedagogical",
        },
        "input_sanitisation": {
            "description": "Block code injection and OS-level commands",
            "penalty": 10.0,
            "type": "security",
        },
        "complexity_bound": {
            "description": "Reject expressions exceeding computational budget",
            "penalty": 5.0,
            "type": "resource",
        },
        "domain_restriction": {
            "description": "Permit math expressions AND natural-language word "
                           "problems; only block symbol garbage",
            "penalty": 8.0,
            "type": "domain",
        },
    }

    BLOCKED_TOKENS = [
        "import ", "exec(", "eval(", "__", "os.", "sys.",
        "subprocess", "open(", "file(", "rm ", "del ",
        "system(", "popen(", "compile(",
    ]

    MAX_EXPRESSION_LENGTH = 500
    PENALTY_THRESHOLD = 5.0

    @classmethod
    def evaluate(cls, expression: str) -> PolicyCheckResult:
        """
        Run the candidate expression through every policy rule.
        Returns a PolicyCheckResult; if penalty_score >= threshold
        the request is pruned from the search space.
        """
        violations: List[str] = []
        penalty = 0.0

        # Security: block injection attempts
        lower = expression.lower()
        for token in cls.BLOCKED_TOKENS:
            if token in lower:
                violations.append(
                    f"Security violation: blocked token '{token.strip()}' detected"
                )
                penalty += cls.POLICIES["input_sanitisation"]["penalty"]

        # Resource: length guard
        if len(expression) > cls.MAX_EXPRESSION_LENGTH:
            violations.append(
                f"Expression exceeds maximum length ({cls.MAX_EXPRESSION_LENGTH} chars)"
            )
            penalty += cls.POLICIES["complexity_bound"]["penalty"]

        # Domain: natural-language word problems are now WELCOME — the model
        # reasons over them and SymPy verifies the arithmetic. So only block
        # obvious garbage: input that is mostly non-alphanumeric symbols rather
        # than real words/numbers. CJK and Latin letters and digits all count as
        # alphanumeric via str.isalnum(), so word problems sail through.
        ok_punct = set(" \t\n\r+-*/^=()[]{}.,，。：:；;？?！!%、…\"'“”‘’`_<>|°")
        weird = sum(1 for c in expression if not (c.isalnum() or c in ok_punct))
        weird_ratio = weird / max(len(expression), 1)
        if weird_ratio > 0.4 and len(expression) > 10:
            violations.append("Input does not look like a math problem or question")
            penalty += cls.POLICIES["domain_restriction"]["penalty"]

        return PolicyCheckResult(
            allowed=penalty < cls.PENALTY_THRESHOLD,
            violations=violations,
            penalty_score=penalty,
        )

    @classmethod
    def get_active_policies(cls) -> List[Dict]:
        return [
            {"name": k, **v}
            for k, v in cls.POLICIES.items()
        ]

# ═══════════════════════════════════════════════════════════════════════
#  NEURO-SYMBOLIC VERIFICATION ENGINE
# ═══════════════════════════════════════════════════════════════════════

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def safe_parse(expr_str: str):
    """Parse an expression string into a SymPy object with safety transforms."""
    cleaned = expr_str.replace("^", "**").strip()
    return parse_expr(cleaned, transformations=TRANSFORMATIONS)


def _looks_like_natural_language(expr_str: str) -> bool:
    """True when the input is prose / a word problem rather than a bare formal
    expression. SymPy's parser will happily turn "小明有3个苹果" (or "John has 3
    apples") into a product of junk symbols and report it "solved", so we detect
    such input up front and let SymPy decline it (callers then defer to Claude).

    Triggers on: a question mark; any non-ASCII letter (e.g. CJK); or — after a
    trial parse — any multi-character alphabetic free symbol, which only arises
    from prose (genuine elementary variables are single letters; sin/cos/pi are
    functions/constants, not free symbols)."""
    if "?" in expr_str or "？" in expr_str:
        return True
    if any(c.isalpha() and ord(c) > 127 for c in expr_str):
        return True
    # The parser splits identifiers into single-char symbols, so prose explodes
    # into many free symbols while an elementary formula has at most a couple of
    # variables. >3 distinct free symbols ⇒ almost certainly a word problem.
    try:
        expr = safe_parse(expr_str.split("=")[0])
        if len(expr.free_symbols) > 3:
            return True
    except Exception:
        pass
    return False


class NeuroSymbolicEngine:
    """
    Bridges natural-language (neural) understanding with formal-language
    (symbolic) verification via SymPy CAS.

    Implements the NL-FL Hybrid Reasoning pattern:
      1. Parse the user's expression into a formal SymPy object
      2. Classify the problem type
      3. Generate deterministic step-by-step solution
      4. Verify each step symbolically
      5. Package results for the Socratic Engine
    """

    @staticmethod
    def classify_problem(expr_str: str) -> Dict[str, Any]:
        """Classify the mathematical problem and extract metadata."""
        classification = {
            "type": "unknown",
            "has_variable": False,
            "variables": [],
            "is_equation": "=" in expr_str,
            "complexity": "basic",
            "topic": "arithmetic",
        }

        try:
            if "=" in expr_str:
                parts = expr_str.split("=")
                lhs = safe_parse(parts[0])
                rhs = safe_parse(parts[1])
                equation = Eq(lhs, rhs)
                free = equation.free_symbols
                classification["has_variable"] = len(free) > 0
                classification["variables"] = [str(s) for s in free]

                if len(free) == 1:
                    var = list(free)[0]
                    try:
                        poly = Poly(lhs - rhs, var)
                        deg = poly.degree()
                        if deg == 1:
                            classification["type"] = "linear_equation"
                            classification["topic"] = "algebra"
                            classification["complexity"] = "basic"
                        elif deg == 2:
                            classification["type"] = "quadratic_equation"
                            classification["topic"] = "algebra"
                            classification["complexity"] = "intermediate"
                        elif deg > 2:
                            classification["type"] = "polynomial_equation"
                            classification["topic"] = "algebra"
                            classification["complexity"] = "advanced"
                    except Exception:
                        classification["type"] = "equation"
                        classification["topic"] = "algebra"
                elif len(free) > 1:
                    classification["type"] = "system_equation"
                    classification["topic"] = "algebra"
                    classification["complexity"] = "intermediate"
                else:
                    classification["type"] = "identity_check"
                    classification["topic"] = "arithmetic"
            else:
                expr = safe_parse(expr_str)
                free = expr.free_symbols
                classification["has_variable"] = len(free) > 0
                classification["variables"] = [str(s) for s in free]

                if len(free) == 0:
                    classification["type"] = "arithmetic"
                    classification["topic"] = "arithmetic"
                else:
                    # Check for calculus keywords
                    if any(k in expr_str.lower() for k in ["diff", "deriv"]):
                        classification["type"] = "derivative"
                        classification["topic"] = "calculus"
                        classification["complexity"] = "intermediate"
                    elif any(k in expr_str.lower() for k in ["integral", "integrate"]):
                        classification["type"] = "integral"
                        classification["topic"] = "calculus"
                        classification["complexity"] = "intermediate"
                    else:
                        classification["type"] = "expression"
                        classification["topic"] = "algebra"

        except Exception:
            classification["type"] = "unparseable"

        return classification

    @staticmethod
    def solve_with_steps(expr_str: str) -> Dict[str, Any]:
        """
        Generate a deterministic, symbolically-verified step-by-step solution.
        Each step is verified by SymPy before being included.
        """
        result = {
            "original": expr_str,
            "classification": NeuroSymbolicEngine.classify_problem(expr_str),
            "latex": "",
            "solution": None,
            "verified_steps": [],
            "verification_status": "pending",
        }

        # Natural-language word problems parse into junk symbols; don't pretend to
        # solve them. Mark unparseable (solution stays None) so the grader defers
        # to Claude and prompts know SymPy has no verified result here.
        if _looks_like_natural_language(expr_str):
            result["verification_status"] = "unparseable"
            return result

        try:
            if "=" in expr_str:
                parts = expr_str.split("=")
                lhs = safe_parse(parts[0])
                rhs = safe_parse(parts[1])
                equation = Eq(lhs, rhs)
                result["latex"] = latex(equation)
                free = equation.free_symbols

                if len(free) == 1:
                    var = list(free)[0]
                    solution = solve(equation, var)
                    result["solution"] = [str(s) for s in solution]

                    # Build verified steps
                    steps = NeuroSymbolicEngine._build_equation_steps(
                        lhs, rhs, var, solution
                    )
                    result["verified_steps"] = steps
                    result["verification_status"] = "verified"
                elif len(free) == 0:
                    # Identity check
                    is_true = simplify(lhs - rhs) == 0
                    result["solution"] = [str(is_true)]
                    result["verified_steps"] = [{
                        "step": 1,
                        "action": "Verify identity",
                        "description": f"Check if {latex(lhs)} equals {latex(rhs)}",
                        "result_latex": f"\\text{{{is_true}}}",
                        "verified": True,
                    }]
                    result["verification_status"] = "verified"
                else:
                    solution = solve(equation)
                    result["solution"] = [str(s) for s in solution] if solution else []
                    result["verification_status"] = "partial"
            else:
                expr = safe_parse(expr_str)
                result["latex"] = latex(expr)
                simplified = simplify(expr)
                result["solution"] = [str(simplified)]

                steps = []
                if expr != simplified:
                    steps.append({
                        "step": 1,
                        "action": "Simplify the expression",
                        "description": f"We start with ${latex(expr)}$",
                        "result_latex": latex(expr),
                        "verified": True,
                    })
                    # Try factoring
                    factored = factor(expr)
                    if factored != expr:
                        steps.append({
                            "step": 2,
                            "action": "Factor",
                            "description": f"Factoring gives us ${latex(factored)}$",
                            "result_latex": latex(factored),
                            "verified": True,
                        })
                    steps.append({
                        "step": len(steps) + 1,
                        "action": "Final simplification",
                        "description": f"The simplified form is ${latex(simplified)}$",
                        "result_latex": latex(simplified),
                        "verified": True,
                    })
                else:
                    steps.append({
                        "step": 1,
                        "action": "Evaluate",
                        "description": f"The expression ${latex(expr)}$ is already in simplest form",
                        "result_latex": latex(simplified),
                        "verified": True,
                    })

                result["verified_steps"] = steps
                result["verification_status"] = "verified"

        except SympifyError as e:
            result["verification_status"] = "error"
            result["verified_steps"] = [{
                "step": 1,
                "action": "Parse error",
                "description": f"Could not parse the expression: {str(e)}",
                "result_latex": "",
                "verified": False,
            }]
        except Exception as e:
            result["verification_status"] = "error"
            result["verified_steps"] = [{
                "step": 1,
                "action": "Processing error",
                "description": f"An error occurred during analysis: {str(e)}",
                "result_latex": "",
                "verified": False,
            }]

        return result

    @staticmethod
    def _build_equation_steps(lhs, rhs, var, solution) -> List[Dict]:
        """Build verified steps for solving an equation."""
        steps = []
        step_num = 1

        # Step 1: Identify the equation
        steps.append({
            "step": step_num,
            "action": "Identify the equation",
            "description": f"We have the equation ${latex(Eq(lhs, rhs))}$",
            "result_latex": latex(Eq(lhs, rhs)),
            "verified": True,
        })
        step_num += 1

        # Step 2: Rearrange — move everything to one side
        combined = simplify(lhs - rhs)
        steps.append({
            "step": step_num,
            "action": "Rearrange",
            "description": f"Move all terms to one side: ${latex(combined)} = 0$",
            "result_latex": f"{latex(combined)} = 0",
            "verified": simplify(lhs - rhs - combined) == 0,
        })
        step_num += 1

        # Step 3: Attempt to factor
        factored = factor(combined)
        if factored != combined:
            steps.append({
                "step": step_num,
                "action": "Factor",
                "description": f"Factoring: ${latex(factored)} = 0$",
                "result_latex": f"{latex(factored)} = 0",
                "verified": simplify(factored - combined) == 0,
            })
            step_num += 1

        # Step 4: Solve for the variable
        if solution:
            sol_latex = ", ".join([f"{latex(var)} = {latex(s)}" for s in solution])
            # Verify each solution
            all_verified = True
            for s in solution:
                check = simplify(lhs.subs(var, s) - rhs.subs(var, s))
                if check != 0:
                    all_verified = False

            steps.append({
                "step": step_num,
                "action": "Solve",
                "description": f"Solution: ${sol_latex}$",
                "result_latex": sol_latex,
                "verified": all_verified,
            })
            step_num += 1

            # Step 5: Verification
            for s in solution:
                lhs_val = simplify(lhs.subs(var, s))
                rhs_val = simplify(rhs.subs(var, s))
                verified = simplify(lhs_val - rhs_val) == 0
                steps.append({
                    "step": step_num,
                    "action": "Verify",
                    "description": (
                        f"Substituting ${latex(var)} = {latex(s)}$: "
                        f"LHS = ${latex(lhs_val)}$, RHS = ${latex(rhs_val)}$ "
                        f"{'✓ Verified!' if verified else '✗ Check failed'}"
                    ),
                    "result_latex": f"{latex(lhs_val)} = {latex(rhs_val)}",
                    "verified": verified,
                })
                step_num += 1

        return steps

# ═══════════════════════════════════════════════════════════════════════
#  SOCRATIC ENGINE — Guided Learning with Progressive Hints
# ═══════════════════════════════════════════════════════════════════════

class SocraticEngine:
    """
    Implements the Socratic tutoring methodology as a non-bypassable constraint.

    The system is architecturally FORBIDDEN from outputting final resolutions
    directly. Instead it enforces guided learning:
      "Break the problem down into steps, explain the underlying logic,
       and never output the final answer immediately."

    Hint levels:
      0 — Problem restatement + what type of problem is this?
      1 — Strategy hint (what approach should we use?)
      2 — First concrete step (show the first manipulation)
      3 — Detailed walkthrough (most steps, but user must do the final step)
      4 — Full guided solution with verification (still framed as teaching)
    """

    @staticmethod
    def generate_socratic_response(
        engine_result: Dict[str, Any],
        hint_level: int = 0,
        adaptive_context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Generate a Socratic response at the specified hint level."""

        classification = engine_result.get("classification", {})
        steps = engine_result.get("verified_steps", [])
        problem_type = classification.get("type", "unknown")
        variables = classification.get("variables", [])
        topic = classification.get("topic", "math")
        original = engine_result.get("original", "")
        eq_latex = engine_result.get("latex", original)

        # Adapt tone based on experience memory
        encouraging = True
        if adaptive_context:
            if adaptive_context.get("is_advanced"):
                encouraging = False  # more direct for advanced users

        response = {
            "hint_level": hint_level,
            "messages": [],
            "can_reveal_more": hint_level < 4,
            "topic": topic,
            "problem_type": problem_type,
            "latex": eq_latex,
            "guardrail_active": True,
            "verification_status": engine_result.get("verification_status", "pending"),
        }

        if hint_level == 0:
            response["messages"] = SocraticEngine._level_0(
                original, eq_latex, classification, encouraging
            )
        elif hint_level == 1:
            response["messages"] = SocraticEngine._level_1(
                original, eq_latex, classification, steps, encouraging
            )
        elif hint_level == 2:
            response["messages"] = SocraticEngine._level_2(
                original, eq_latex, classification, steps, encouraging
            )
        elif hint_level == 3:
            response["messages"] = SocraticEngine._level_3(
                original, eq_latex, classification, steps, encouraging
            )
        elif hint_level >= 4:
            response["messages"] = SocraticEngine._level_4(
                original, eq_latex, classification, steps, engine_result, encouraging
            )

        return response

    @staticmethod
    def _level_0(original, eq_latex, classification, encouraging) -> List[Dict]:
        """Problem recognition — restate and classify."""
        msgs = []
        problem_type = classification.get("type", "unknown")
        topic = classification.get("topic", "math")
        variables = classification.get("variables", [])

        if encouraging:
            msgs.append({
                "role": "tutor",
                "content": f"Great question! Let's work through this together. 🧠",
                "type": "encouragement",
            })

        msgs.append({
            "role": "tutor",
            "content": f"I see the expression: ${eq_latex}$",
            "type": "observation",
        })

        type_descriptions = {
            "linear_equation": "This is a **linear equation** — it has a variable raised to the first power.",
            "quadratic_equation": "This is a **quadratic equation** — the variable is raised to the second power.",
            "polynomial_equation": "This is a **polynomial equation** of higher degree.",
            "arithmetic": "This is an **arithmetic expression** we can evaluate.",
            "expression": "This is an **algebraic expression** we can simplify.",
            "identity_check": "This looks like an **identity** we can verify.",
        }

        desc = type_descriptions.get(problem_type, f"This is a **{topic}** problem.")
        msgs.append({"role": "tutor", "content": desc, "type": "classification"})

        if variables:
            var_str = ", ".join([f"${v}$" for v in variables])
            msgs.append({
                "role": "tutor",
                "content": f"🔍 **Think about it:** What do we need to find? We're looking for the value(s) of {var_str}.",
                "type": "question",
            })
        else:
            msgs.append({
                "role": "tutor",
                "content": "🔍 **Think about it:** What operations can we apply to simplify this?",
                "type": "question",
            })

        msgs.append({
            "role": "tutor",
            "content": "💡 When you're ready for a hint on how to start, click **Next Hint**!",
            "type": "prompt",
        })

        return msgs

    @staticmethod
    def _level_1(original, eq_latex, classification, steps, encouraging) -> List[Dict]:
        """Strategy hint — what approach to use."""
        msgs = []
        problem_type = classification.get("type", "unknown")

        strategy_hints = {
            "linear_equation": (
                "For a linear equation, our strategy is to **isolate the variable** on one side. "
                "We do this by performing the same operation on both sides of the equation."
            ),
            "quadratic_equation": (
                "For a quadratic equation, we have several strategies: "
                "**factoring**, the **quadratic formula**, or **completing the square**. "
                "Can you tell which might work here?"
            ),
            "polynomial_equation": (
                "For polynomial equations, we can try **factoring**, **synthetic division**, "
                "or look for **rational roots**."
            ),
            "arithmetic": (
                "Let's break this calculation into smaller parts. "
                "What's the order of operations (PEMDAS/BODMAS) we should follow?"
            ),
            "expression": (
                "To simplify this expression, look for **like terms** to combine "
                "or **common factors** to pull out."
            ),
        }

        hint = strategy_hints.get(
            problem_type,
            "Let's think about what mathematical tools we can apply here."
        )

        msgs.append({"role": "tutor", "content": f"📋 **Strategy:** {hint}", "type": "strategy"})

        # Give a concrete starting question
        if problem_type == "linear_equation" and len(steps) > 1:
            msgs.append({
                "role": "tutor",
                "content": "🤔 **Your turn:** Look at both sides of the equation. What operation would you perform first to start isolating the variable?",
                "type": "question",
            })
        elif problem_type == "quadratic_equation":
            msgs.append({
                "role": "tutor",
                "content": "🤔 **Your turn:** First, can you rearrange the equation so that one side equals zero?",
                "type": "question",
            })
        else:
            msgs.append({
                "role": "tutor",
                "content": "🤔 **Your turn:** What would be your first step? Try it and click **Next Hint** to check!",
                "type": "question",
            })

        return msgs

    @staticmethod
    def _level_2(original, eq_latex, classification, steps, encouraging) -> List[Dict]:
        """First concrete step — show the first manipulation."""
        msgs = []

        if len(steps) >= 2:
            step = steps[1]  # Skip the "identify" step, show the first real step
            verified_badge = " ✅" if step.get("verified") else ""
            msgs.append({
                "role": "tutor",
                "content": f"**Step {step['step']}: {step['action']}**{verified_badge}",
                "type": "step_header",
            })
            msgs.append({
                "role": "tutor",
                "content": step["description"],
                "type": "step_detail",
            })
            msgs.append({
                "role": "tutor",
                "content": "🧩 **Now it's your turn:** Can you carry out the next step from here? What would you do next?",
                "type": "question",
            })
        else:
            msgs.append({
                "role": "tutor",
                "content": "Let's start by carefully examining each term in the expression.",
                "type": "guidance",
            })

        return msgs

    @staticmethod
    def _level_3(original, eq_latex, classification, steps, encouraging) -> List[Dict]:
        """Detailed walkthrough — most steps but user does the final one."""
        msgs = []

        msgs.append({
            "role": "tutor",
            "content": "📝 Let me walk you through most of the solution. **Try to complete the final step yourself!**",
            "type": "guidance",
        })

        # Show all steps except the last one
        steps_to_show = steps[:-1] if len(steps) > 1 else steps
        for step in steps_to_show:
            verified_badge = " ✅" if step.get("verified") else ""
            msgs.append({
                "role": "tutor",
                "content": f"**Step {step['step']}: {step['action']}**{verified_badge}\n{step['description']}",
                "type": "step",
            })

        if len(steps) > 1:
            msgs.append({
                "role": "tutor",
                "content": "🎯 **Final challenge:** Based on the steps above, can you determine the answer? Click **Next Hint** to check your work!",
                "type": "challenge",
            })
        else:
            msgs.append({
                "role": "tutor",
                "content": "🎯 **Try it:** Apply what we discussed and attempt the solution!",
                "type": "challenge",
            })

        return msgs

    @staticmethod
    def _level_4(original, eq_latex, classification, steps, engine_result, encouraging) -> List[Dict]:
        """Full guided solution with verification. Still framed as teaching."""
        msgs = []

        msgs.append({
            "role": "tutor",
            "content": "📖 Here's the complete walkthrough. Study each step to understand the logic!",
            "type": "guidance",
        })

        for step in steps:
            verified_badge = " ✅ *Verified by CAS*" if step.get("verified") else ""
            msgs.append({
                "role": "tutor",
                "content": f"**Step {step['step']}: {step['action']}**{verified_badge}\n{step['description']}",
                "type": "step",
            })

        # Add learning reflection
        msgs.append({
            "role": "tutor",
            "content": "🌟 **Reflection:** Now that you've seen the full solution, can you explain *why* each step works? Understanding the *why* is more important than the *what*!",
            "type": "reflection",
        })

        # Add verification summary
        all_verified = all(s.get("verified", False) for s in steps)
        if all_verified:
            msgs.append({
                "role": "system",
                "content": "✅ All steps have been **symbolically verified** by the SymPy Computer Algebra System. This solution is mathematically guaranteed to be correct.",
                "type": "verification",
            })
        else:
            msgs.append({
                "role": "system",
                "content": "⚠️ Some steps could not be fully verified symbolically. Please double-check the reasoning.",
                "type": "verification",
            })

        return msgs

# ═══════════════════════════════════════════════════════════════════════
#  BLENDING INSTRUCTIONS ENGINE
# ═══════════════════════════════════════════════════════════════════════

class BlendingInstructions:
    """
    Dynamically compiles blended instruction payloads that fuse:
      1. Strategic Intent  — the user's requirement
      2. Contextual Grounding  — session history and problem metadata
      3. Execution Directives  — permitted operations and formatting
      4. Architectural Boundaries  — immutable constraints
    """

    @staticmethod
    def compile(
        expression: str,
        session_id: str,
        action: str = "solve",
    ) -> Dict[str, Any]:

        adaptive = memory.get_adaptive_context(session_id)
        classification = NeuroSymbolicEngine.classify_problem(expression)

        return {
            "strategic_intent": {
                "goal": f"Help the user understand how to {action} '{expression}'",
                "method": "Socratic guided learning",
                "constraint": "NEVER reveal the final answer without guided steps",
            },
            "contextual_grounding": {
                "problem_classification": classification,
                "session_context": adaptive,
                "conversation_length": len(memory.get_conversation(session_id)),
            },
            "execution_directives": {
                "permitted_operations": ["simplify", "factor", "solve", "expand", "verify"],
                "output_format": "step-by-step with LaTeX",
                "verification_required": True,
                "cas_engine": "SymPy",
            },
            "architectural_boundaries": {
                "immutable_policies": PolicyEngine.get_active_policies(),
                "max_hint_level": 4,
                "socratic_constraint_active": True,
                "direct_answer_forbidden": True,
            },
        }

# ═══════════════════════════════════════════════════════════════════════
#  DATA MANAGER — Architecture Metadata as JSON Tree
# ═══════════════════════════════════════════════════════════════════════

def build_architecture_tree() -> Dict:
    """
    Build the hierarchical JSON metadata tree that describes the
    application's architecture, enabling agents to comprehend the
    macro-architecture instantly.
    """
    return {
        "id": "root",
        "name": "AI Math Tutor",
        "version": "2.0.0",
        "type": "system",
        "layers": [
            {
                "id": "layer-1",
                "name": "Frontend Interface Layer",
                "type": "layer",
                "purpose": "User engagement, multimodal input (canvas/text/voice), OCR pipeline",
                "status": "active",
                "components": [
                    {"id": "c-canvas", "name": "CanvasBoard", "type": "component", "purpose": "P5.js drawing surface with stroke capture", "status": "active"},
                    {"id": "c-sidebar", "name": "Sidebar", "type": "component", "purpose": "Input controls, voice, and result display", "status": "active"},
                    {"id": "c-arch-viz", "name": "ArchitectureVisualizer", "type": "component", "purpose": "Real-time system architecture visualization", "status": "active"},
                    {"id": "c-conversation", "name": "SocraticConversation", "type": "component", "purpose": "Chat-style Socratic dialogue interface", "status": "active"},
                ],
            },
            {
                "id": "layer-2",
                "name": "Orchestration & Logic Layer",
                "type": "layer",
                "purpose": "Request routing, session management, evolution trigger, blending instruction compilation",
                "status": "active",
                "components": [
                    {"id": "c-router", "name": "API Router", "type": "component", "purpose": "FastAPI endpoint routing (Router Pattern)", "status": "active"},
                    {"id": "c-blending", "name": "Blending Instructions", "type": "component", "purpose": "Dynamic context payload compilation", "status": "active"},
                    {"id": "c-memory", "name": "Experience Memory", "type": "component", "purpose": "Session-based adaptive learning store", "status": "active"},
                ],
            },
            {
                "id": "layer-3",
                "name": "Cognitive Processing Layer",
                "type": "layer",
                "purpose": "Mathematical reasoning, Socratic hint generation, problem classification",
                "status": "active",
                "components": [
                    {"id": "c-socratic", "name": "Socratic Engine", "type": "component", "purpose": "Multi-level guided hint generator with pedagogical guardrails", "status": "active"},
                    {"id": "c-neuro", "name": "Neuro-Symbolic Engine", "type": "component", "purpose": "SymPy CAS integration for deterministic verification", "status": "active"},
                    {"id": "c-classifier", "name": "Problem Classifier", "type": "component", "purpose": "Mathematical problem type detection and metadata extraction", "status": "active"},
                ],
            },
            {
                "id": "layer-4",
                "name": "Execution & Validation Layer",
                "type": "layer",
                "purpose": "Secure sandbox for symbolic computation, step verification, policy enforcement",
                "status": "active",
                "components": [
                    {"id": "c-policy", "name": "Policy Engine (SEPGA)", "type": "component", "purpose": "Compliance-by-design guardrails, penalty scoring, Constrained MDP", "status": "active"},
                    {"id": "c-sandbox", "name": "Verification Sandbox", "type": "component", "purpose": "Isolated symbolic computation environment", "status": "active"},
                    {"id": "c-lattice", "name": "Lattice Framework", "type": "component", "purpose": "Continuous guardrail optimization (risk assessment → case expansion → optimization → evaluation)", "status": "active"},
                ],
            },
        ],
        "agents": [
            {"id": "a-sprint", "name": "Sprint Agent", "role": "Product Manager", "function": "Interprets requirements, decomposes tasks, defines acceptance criteria"},
            {"id": "a-supervisor", "name": "Supervisor Agent", "role": "Engineering Manager", "function": "Allocates resources dynamically based on task complexity"},
            {"id": "a-summary", "name": "Summary Agent", "role": "Technical Writer", "function": "Condenses codebase into structured metadata"},
            {"id": "a-control", "name": "Control Agent", "role": "Systems Architect", "function": "Uses Meta-RAG to localize context and define boundaries"},
            {"id": "a-developer", "name": "Developer Agent", "role": "Software Engineer", "function": "Executes AST patches, writes code, generates tests"},
            {"id": "a-peer", "name": "Peer Agent", "role": "QA / Code Reviewer", "function": "Scrutinizes for vulnerabilities, regressions, hallucinations"},
        ],
    }

# ═══════════════════════════════════════════════════════════════════════
#  PROBLEM BANK — Random practice problems
# ═══════════════════════════════════════════════════════════════════════

class Problem(BaseModel):
    id: str
    title: str
    statement: str          # human-readable prompt (what the student must do)
    latex: str              # the formula/expression to render
    difficulty: str         # "easy" | "medium" | "hard"
    topic: str
    source: Optional[str] = None   # "opentdb" | "local"

# Curated bank of practice problems. The student writes their solution on the
# whiteboard or via voice/text — so we intentionally do NOT ship answer choices.
PROBLEM_BANK: List[Dict[str, Any]] = [
    {
        "id": "alg-001",
        "title": "Solve the Linear Equation",
        "statement": "Find the value of x that satisfies the equation.",
        "latex": "3x + 7 = 22",
        "difficulty": "easy",
        "topic": "Algebra",
    },
    {
        "id": "alg-002",
        "title": "Factor and Solve",
        "statement": "Solve the quadratic equation by factoring.",
        "latex": "x^2 - 5x + 6 = 0",
        "difficulty": "medium",
        "topic": "Algebra",
    },
    {
        "id": "alg-003",
        "title": "Simplify the Expression",
        "statement": "Simplify the algebraic expression as far as possible.",
        "latex": "\\frac{x^2 - 9}{x - 3}",
        "difficulty": "medium",
        "topic": "Algebra",
    },
    {
        "id": "cal-001",
        "title": "Find the Derivative",
        "statement": "Differentiate the function with respect to x.",
        "latex": "f(x) = 3x^2 + 2x - 5",
        "difficulty": "medium",
        "topic": "Calculus",
    },
    {
        "id": "cal-002",
        "title": "Evaluate the Integral",
        "statement": "Compute the indefinite integral.",
        "latex": "\\int (4x^3 + 1)\\,dx",
        "difficulty": "hard",
        "topic": "Calculus",
    },
    {
        "id": "trg-001",
        "title": "Solve for the Angle",
        "statement": "Find all angles in [0, 2π) that satisfy the equation.",
        "latex": "2\\sin(\\theta) = 1",
        "difficulty": "hard",
        "topic": "Trigonometry",
    },
    {
        "id": "geo-001",
        "title": "Area of a Circle",
        "statement": "A circle has radius r = 5. Find its exact area.",
        "latex": "A = \\pi r^2,\\quad r = 5",
        "difficulty": "easy",
        "topic": "Geometry",
    },
    {
        "id": "ari-001",
        "title": "Order of Operations",
        "statement": "Evaluate the expression using the correct order of operations.",
        "latex": "6 + 2 \\times (3^2 - 4)",
        "difficulty": "easy",
        "topic": "Arithmetic",
    },
]


# ── Open Trivia Database (OpenTDB) provider ─────────────────────────────
#
# Pulls live questions from https://opentdb.com (the "Science: Mathematics"
# category, id 19) and normalizes them into our Problem shape. OpenTDB returns
# HTML-encoded multiple-choice questions, so we unescape the text and render the
# shuffled answer options as a LaTeX-safe block in the `latex` field.
#
# OpenTDB rate-limits to ~1 request / 5s per IP, so we fetch a batch and serve
# from an in-memory cache, refilling only when it runs dry. Any network failure
# falls back silently to the curated PROBLEM_BANK above.

class OpenTDBProvider:
    BASE_URL = "https://opentdb.com/api.php"
    CATEGORY_MATH = 19          # "Science: Mathematics"
    BATCH_SIZE = 30             # questions to pull per network call
    _cache: List[Dict[str, Any]] = []

    # LaTeX text-mode escapes so answer text never breaks MathJax rendering.
    _LATEX_ESCAPES = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }

    @classmethod
    def _latex_escape(cls, text: str) -> str:
        return "".join(cls._LATEX_ESCAPES.get(c, c) for c in text)

    @classmethod
    def _normalize(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        """Map one OpenTDB result into our Problem dict."""
        question = html_lib.unescape(item.get("question", ""))
        correct = html_lib.unescape(item.get("correct_answer", ""))
        incorrect = [html_lib.unescape(a) for a in item.get("incorrect_answers", [])]

        if item.get("type") == "boolean":
            latex_block = r"\text{True} \qquad \text{False}"
        else:
            options = incorrect + [correct]
            random.shuffle(options)
            labels = ["A", "B", "C", "D", "E", "F"]
            parts = [
                rf"\text{{{lbl}) }} \text{{{cls._latex_escape(opt)}}}"
                for lbl, opt in zip(labels, options)
            ]
            latex_block = r" \qquad ".join(parts)

        difficulty = item.get("difficulty", "medium")
        return {
            "id": "otdb-" + uuid4().hex[:8],
            "title": f"Math Trivia ({difficulty.capitalize()})",
            "statement": question,
            "latex": latex_block,
            "difficulty": difficulty,
            "topic": "Trivia",
            "source": "opentdb",
        }

    @classmethod
    def _fetch_batch(cls, amount: int, difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
        """Hit the OpenTDB API and return normalized problems (or [] on failure)."""
        # Matches the API form https://opentdb.com/api.php?amount=N&category=19
        # (no `type` filter, so both multiple-choice and true/false come through).
        params = {"amount": amount, "category": cls.CATEGORY_MATH}
        if difficulty in ("easy", "medium", "hard"):
            params["difficulty"] = difficulty
        url = cls.BASE_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "math-tutor-demo/2.0"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # URLError, timeout, JSON errors, etc.
            print(f"[OpenTDB] fetch failed: {exc}")
            return []
        # response_code 0 == success; anything else (no results, rate-limited) -> []
        if data.get("response_code") != 0:
            print(f"[OpenTDB] non-zero response_code: {data.get('response_code')}")
            return []
        return [cls._normalize(item) for item in data.get("results", [])]

    @classmethod
    def get_random(cls, difficulty: Optional[str] = None,
                   exclude_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return one normalized problem, or None if OpenTDB is unreachable."""
        if difficulty:
            # Difficulty-filtered requests fetch their own small batch.
            pool = cls._fetch_batch(amount=10, difficulty=difficulty)
        else:
            if not cls._cache:
                cls._cache = cls._fetch_batch(amount=cls.BATCH_SIZE)
            pool = cls._cache

        if exclude_id and len(pool) > 1:
            pool = [p for p in pool if p["id"] != exclude_id]
        if not pool:
            return None

        choice = random.choice(pool)
        # Consume from the shared cache so "New Problem" keeps advancing.
        if not difficulty:
            try:
                cls._cache.remove(choice)
            except ValueError:
                pass
        return choice

    @classmethod
    def get_many(cls, amount: int = 20,
                 difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
        return cls._fetch_batch(amount=amount, difficulty=difficulty)


def _tag_local(problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stamp curated bank problems with their source for API transparency."""
    return [{**p, "source": p.get("source", "local")} for p in problems]


@app.get("/problems")
def list_problems(
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    source: str = "opentdb",
):
    """
    Return a list of problems.

    `source`:
      • "opentdb" (default) — live questions from the Open Trivia Database
      • "local"             — the curated static bank
      • "mixed"             — OpenTDB questions plus the local bank

    Falls back to the local bank if OpenTDB is unreachable.
    """
    items: List[Dict[str, Any]] = []

    if source in ("opentdb", "mixed"):
        items += OpenTDBProvider.get_many(amount=20, difficulty=difficulty)
    if source in ("local", "mixed") or (source == "opentdb" and not items):
        items += _tag_local(PROBLEM_BANK)

    if topic:
        items = [p for p in items if p["topic"].lower() == topic.lower()]
    if difficulty:
        items = [p for p in items if p["difficulty"].lower() == difficulty.lower()]

    return {"count": len(items), "source": source, "problems": items}


@app.get("/problems/random", response_model=Problem)
def random_problem(
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    exclude_id: Optional[str] = None,
    source: str = "opentdb",
):
    """
    Return a single random practice problem.

    By default this pulls a live question from the Open Trivia Database
    ("Science: Mathematics" category). Pass `source=local` for the curated bank.

    Optional filters: `topic`, `difficulty`. `exclude_id` avoids handing back the
    problem currently on screen (so "New Problem" always changes something).
    If OpenTDB is unreachable, it falls back to the local bank automatically.
    """
    # Try OpenTDB first (unless the caller explicitly asked for the local bank).
    if source != "local":
        problem = OpenTDBProvider.get_random(difficulty=difficulty, exclude_id=exclude_id)
        if problem:
            return problem
        # else: OpenTDB unreachable — fall through to the local bank.

    pool = _tag_local(PROBLEM_BANK)
    if topic:
        pool = [p for p in pool if p["topic"].lower() == topic.lower()]
    if difficulty:
        pool = [p for p in pool if p["difficulty"].lower() == difficulty.lower()]
    if exclude_id and len(pool) > 1:
        pool = [p for p in pool if p["id"] != exclude_id]

    if not pool:
        raise HTTPException(status_code=404, detail="No problems match the given filters")

    return random.choice(pool)


# ── Practice feed: own question bank (exams.db) + AI generation ──────────
#
# The core tutoring UI (demo_standalone.html) draws practice problems from the
# project's OWN bank — questions written by AI (/exam/generate) or seeded from
# templates — instead of the external OpenTDB trivia feed above. This keeps the
# practice stream on-topic (Chinese elementary math) and aligned with the
# de-symbolization direction. /problems(/random) remain as legacy endpoints.

# Per-source notice rendered BELOW the question (not part of the statement). The
# AI disclaimer is mandatory on AI-generated questions so students discern them.
_SOURCE_DISCLAIMERS: Dict[str, str] = {
    "ai": "本题由 AI 生成，请注意甄别。",
    "xueke": "本题来自学科网题库。",
}


def _source_disclaimer(source: Optional[str]) -> Optional[str]:
    return _SOURCE_DISCLAIMERS.get((source or "").strip().lower())


def _bank_to_card(q: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt an exams.db question into the frontend problem-card shape."""
    qtags = q.get("tags", []) or []
    primary = next((t for t in qtags if t.get("primary")), qtags[0] if qtags else None)
    topic = ((primary or {}).get("subdimension")
             or (primary or {}).get("tag") or "练习")
    diff = q.get("difficulty")
    diff_label = f"难度 {diff}" if isinstance(diff, int) else (str(diff) if diff else "练习")
    src = q.get("source", "bank")
    return {
        "id": q.get("id"),
        "title": (primary or {}).get("tag") or "练习题",
        "statement": q.get("statement", "") or "",
        "latex": q.get("latex", "") or "",
        "difficulty": diff_label,
        "topic": topic,
        "tags": qtags,
        "source": src,
        # Notice shown beneath the question (NOT part of the statement). None when
        # the source carries no notice; the AI one is mandatory for 甄别.
        "disclaimer": _source_disclaimer(src),
    }


def _question_tag_row(name: str, primary: bool = False) -> Dict[str, Any]:
    """Map a tag NAME (from tags.db) to a question_tags row, resolving its
    dimension/subdimension from the tag store, falling back to exam's mapping."""
    t = tags.get_tag(name)
    if t and t["kind"] == tags.KIND_LOGIC:
        return {"dimension": exam.DIM_LOGIC, "subdimension": (t.get("parent") or ""),
                "tag": name, "primary": primary}
    dim = exam.tag_dimension(name) or exam.DIM_CORE          # knowledge / unknown
    subdim = exam.tag_subdimension(name) or (t.get("parent") if t else "") or ""
    return {"dimension": dim, "subdimension": subdim, "tag": name, "primary": primary}


def _ai_one_question(grade: Optional[int] = None,
                     focus_logic: Optional[str] = None,
                     target_difficulty: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Generate ONE question AND tag it from the LIVE vocabulary (tags.db) via
    Claude. Existing tags are reused (usage bumped); any tag the model proposes
    when nothing fits is ADDED to the store (the self-evolving loop, source='ai').
    Saves the question with its logic + knowledge tags and an open-ended difficulty.
    `focus_logic` (a weak logic type from diagnosis / user) biases the question to
    TRAIN it; `target_difficulty` requests a difficulty rung. Returns the saved
    bank-question dict, or None on failure / gateway down."""
    if not claude_service.available():
        return None
    k_names = [t["name"] for t in tags.list_tags(kind=tags.KIND_KNOWLEDGE)]
    l_tags = [{"name": t["name"], "move": (t.get("meta") or {}).get("move"),
               "flaw": (t.get("meta") or {}).get("flaw")}
              for t in tags.list_tags(kind=tags.KIND_LOGIC)]
    system = prompts.build_tagged_generation_prompt(
        k_names, l_tags, exam.DIFFICULTY_LEVELS,
        focus_logic=focus_logic, target_difficulty=target_difficulty)
    item = None
    for attempt in range(3):           # retry transient gateway / parse misses
        try:
            text = claude_service.complete(
                system=system,
                messages=[{"role": "user", "content": "请出 1 道题并按要求打标签，只输出 JSON 数组。"}],
                session_id="practice-gen", max_tokens=2000,
                temperature=0.7 + 0.1 * attempt,
            )
        except ClaudeError:
            return None
        arr = _parse_json_array(text)
        if arr and isinstance(arr[0], dict) and (arr[0].get("statement") or "").strip():
            item = arr[0]
            break
    if item is None:
        return None
    statement = (item.get("statement") or "").strip()

    known_k, known_l = set(k_names), {t["name"] for t in l_tags}

    # 1) Self-evolving step: register any NEW tags the model proposed.
    added: List[str] = []
    added_logic: List[str] = []
    added_know: List[str] = []
    for nt in (item.get("new_tags") or []):
        if not isinstance(nt, dict):
            continue
        nm = (nt.get("name") or "").strip()
        kind = (nt.get("kind") or "").strip()
        if not nm or kind not in (tags.KIND_LOGIC, tags.KIND_KNOWLEDGE):
            continue
        tags.add_tag(nm, kind, description=(nt.get("reason") or "").strip() or None, source="ai")
        added.append(nm)
        if kind == tags.KIND_KNOWLEDGE:
            added_know.append(nm); known_k.add(nm)
        else:
            added_logic.append(nm); known_l.add(nm)

    # 2) Resolve chosen tags into question_tags rows; a freshly-added tag is
    #    attached to the very question that prompted it (not just stored).
    chosen_logic = [t for t in (item.get("logic_tags") or []) if t in known_l]
    for nm in added_logic:
        if nm not in chosen_logic:
            chosen_logic.append(nm)
    chosen_know = [t for t in (item.get("knowledge_tags") or []) if t in known_k]
    for nm in added_know:
        if nm not in chosen_know:
            chosen_know.append(nm)
    qtags = [_question_tag_row(nm, primary=(i == 0)) for i, nm in enumerate(chosen_logic)]
    qtags += [_question_tag_row(nm, primary=False) for nm in chosen_know]
    for nm in chosen_logic + chosen_know:
        tags.bump_usage(nm)

    diff = item.get("difficulty")
    try:
        # Open-ended ladder: floor at the minimum anchor, no upper cap.
        diff = max(exam.DIFFICULTY_MIN, int(diff)) if diff is not None else None
    except (ValueError, TypeError):
        diff = None

    q = {
        "statement": statement,
        "latex": (item.get("latex") or "").strip(),
        "answer": (item.get("answer") or "").strip(),
        "grade": grade,
        "difficulty": diff,
        "source": "ai",
        "tags": qtags,
    }
    q["id"] = exam.save_question(q)
    q["new_tags_added"] = added
    return q


# ── 学科网 (Xueke) provider: tag-filtered questions from an external API ──────
#
# The third question source (besides AI-generation and the local bank). Pulls
# questions matching a knowledge/logic tag from 学科网, normalises them into our
# bank-question shape, and PERSISTS them into exams.db with source="xueke" — so
# each one is stamped with a 200-… structured id (see exam._make_id).
#
# The exact 学科网 API contract varies per account, so the endpoint/key live in
# config (XUEKE_*) and `_normalize` accepts several common field spellings. When
# unconfigured or unreachable, methods return None/[] and callers fall back to
# the local bank — same graceful-degradation contract as the OpenTDB provider.
#
# Expected (configurable) response shape, JSON:
#   {"questions": [
#       {"content"|"statement"|"stem": "...",   # the question text (required)
#        "latex": "...",                         # optional rendered math
#        "answer"|"solution": "...",             # optional reference answer
#        "difficulty": 5,                         # optional 1..N
#        "tags": ["..."]}                         # optional extra tags
#   ]}

class XuekeProvider:
    @staticmethod
    def available() -> bool:
        return config.xueke_configured()

    @staticmethod
    def _normalize(item: Dict[str, Any], tag: str) -> Optional[Dict[str, Any]]:
        """Map one 学科网 result into our question dict, or None if it has no
        usable statement. The requested `tag` is always attached so the saved
        question is findable by it."""
        statement = (item.get("content") or item.get("statement")
                     or item.get("stem") or "").strip()
        if not statement:
            return None
        answer = (item.get("answer") or item.get("solution") or "").strip()
        diff = item.get("difficulty")
        try:
            diff = max(exam.DIFFICULTY_MIN, int(diff)) if diff is not None else None
        except (ValueError, TypeError):
            diff = None

        # Build tag rows: the requested tag is primary; any extra tags the API
        # returned are attached too (resolved against the live vocabulary).
        names: List[str] = [tag]
        for extra in (item.get("tags") or []):
            extra = (extra or "").strip() if isinstance(extra, str) else ""
            if extra and extra not in names:
                names.append(extra)
        qtags = [_question_tag_row(nm, primary=(i == 0)) for i, nm in enumerate(names)]

        return {
            "statement": statement,
            "latex": (item.get("latex") or "").strip(),
            "answer": answer,
            "grade": None,
            "difficulty": diff,
            "source": "xueke",
            "tags": qtags,
        }

    @classmethod
    def _fetch(cls, tag: str, amount: int) -> List[Dict[str, Any]]:
        """Query the 学科网 API for questions carrying `tag`. Returns the raw
        result list (or [] on any failure)."""
        params = {"tag": tag, "limit": amount}
        url = config.xueke_endpoint() + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url, headers={"authorization": f"Bearer {config.XUEKE_API_KEY}",
                          "User-Agent": "math-tutor/2.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=config.XUEKE_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # URLError, timeout, JSON errors, etc.
            print(f"[Xueke] fetch failed: {exc}")
            return []
        if isinstance(data, dict):
            return data.get("questions") or data.get("results") or []
        return data if isinstance(data, list) else []

    @classmethod
    def get_by_tag(cls, tag: str) -> Optional[Dict[str, Any]]:
        """Fetch ONE question for `tag`, persist it (gets a 200-… id), and return
        the saved bank-question dict. None if unconfigured/unreachable/empty."""
        if not cls.available() or not tag:
            return None
        for item in cls._fetch(tag, amount=5):
            if not isinstance(item, dict):
                continue
            q = cls._normalize(item, tag)
            if q is None:
                continue
            for row in q["tags"]:
                tags.bump_usage(row["tag"])
            q["id"] = exam.save_question(q)
            return q
        return None


@app.get("/practice/next")
def practice_next(exclude_id: Optional[str] = None, generate: bool = False,
                  focus_logic: Optional[str] = None, difficulty: Optional[int] = None,
                  adaptive: Optional[str] = None, source: Optional[str] = None,
                  tag: Optional[str] = None):
    """One practice problem for the core tutoring UI — the 出题 pipeline.

    Source of truth is the project's OWN bank (exams.db) — NOT external OpenTDB.
    The 出题方式 is chosen with `source` (the design's three-way choice); the
    flags below are conveniences that imply a source:
      • source=bank (default) → a random question from the existing bank
      • source=ai / ?generate=1 → generate a fresh AI question (gateway up), else bank
      • source=xueke&tag=X    → pull a 学科网 question carrying tag X, else bank
      • ?focus_logic=X        → AI-generate one that TRAINS logic type X
      • ?difficulty=N         → AI-generate one at about difficulty N (open-ended)
      • ?adaptive=<sid>       → AI-generate one targeting THIS session's weakest
                                logic type (from diagnosis); generation is implied
    An empty bank is auto-seeded with template questions, so the UI always works
    even offline. Replaces the old /problems/random (OpenTDB) data path.
    """
    source = (source or "").strip().lower() or None

    # 学科网: pull by tag, persist (→ 200-… id), serve; else fall through to bank.
    if source == "xueke":
        q = XuekeProvider.get_by_tag(tag or focus_logic or "")
        if q is not None:
            return {**_bank_to_card(q), "generated": False, "from_source": "xueke"}

    # Adaptive: derive the focus from the session's diagnosed weakest logic type.
    if adaptive and not focus_logic:
        weak = diagnosis.weak_logic_tags(adaptive, limit=1)
        focus_logic = weak[0] if weak else None
    if source == "ai" or adaptive or focus_logic or difficulty is not None:
        generate = True

    if generate:                       # opt-in AI generation, bank as fallback
        q = _ai_one_question(focus_logic=focus_logic, target_difficulty=difficulty)
        if q is not None:
            return {**_bank_to_card(q), "generated": True, "from_source": "ai",
                    "focus_logic": focus_logic, "target_difficulty": difficulty}

    q = exam.random_question(exclude_id=exclude_id)
    if q is None:                      # empty bank → seed templates, then serve
        exam.seed_templates()
        q = exam.random_question(exclude_id=exclude_id)
    if q is None:
        raise HTTPException(status_code=503, detail="题库为空且无法生成题目")
    return {**_bank_to_card(q), "generated": False, "from_source": "bank"}


# ═══════════════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.get("/")
def read_root():
    return {
        "message": "Self-Evolving AI Math Tutor Backend v2.0",
        "architecture": "Multi-layered (Frontend → Orchestration → Cognitive → Validation)",
        "subsystems": [
            "Socratic Engine",
            "Neuro-Symbolic Verification (SymPy CAS)",
            "Policy Engine (SEPGA)",
            "Experience Memory",
            "Blending Instructions",
            "Data Manager",
        ],
    }


@app.get("/recognize/models")
def recognize_models():
    """List the OCR engines the select screen can choose from (drives the
    「选择 OCR 模型」dropdown). Each model's ``id`` is the ``method`` value to pass
    back to ``POST /recognize``. See recognize.list_models()."""
    return recognize.list_models()


@app.post("/recognize")
async def recognize_math(file: UploadFile = File(...), method: str = "nex"):
    """
    Handwriting OCR endpoint — the 作答 pipeline's 笔画→文字 step.

    The whiteboard PNG submitted by the student is turned into *text* (that
    string, not the picture, is what the frontend then feeds into /analyze).
    `method` selects the design's two paths:
      • "nex"    (default) — render → nex-n2-pro specialised OCR (path 1)
      • "claude"           — hand the drawing to Claude vision (path 2)
      • "auto"             — try nex first, fall back to Claude on miss/failure

    Falls back to a mock expression when neither gateway is configured so the
    demo still works end-to-end before the .env is filled in.
    """
    image_bytes = await file.read()
    method = (method or "nex").strip().lower()

    # recognize_* make a BLOCKING HTTP call (urllib) that can take many seconds.
    # Running it directly in this async endpoint would freeze the event loop;
    # offload to a worker thread so the server stays responsive.
    if method == "claude":
        result = await run_in_threadpool(recognize.recognize_via_claude, image_bytes)
        engine = "claude-vision"
    else:
        result = await run_in_threadpool(recognize.recognize_detailed, image_bytes)
        engine = "nex-n2-pro"
        # auto: if nex produced nothing usable, retry with Claude vision (path 2).
        if method == "auto" and result.get("status") != "ok" \
                and recognize.claude_vision_available():
            alt = await run_in_threadpool(recognize.recognize_via_claude, image_bytes)
            if alt.get("status") == "ok":
                result, engine = alt, "claude-vision"

    status = result.get("status")
    if status == "ok":
        return {"text": result["text"], "engine": engine, "status": "ok"}

    if status == "unconfigured":
        # No OCR gateway configured — keep the demo functional with a mock.
        return {"text": "2*x + 5 = 15", "engine": "mock", "status": "unconfigured"}

    # empty / timeout / error — surface the reason so the UI shows a useful note.
    return {"text": "", "engine": engine, "status": status}


def generate_socratic(engine_result, hint_level, adaptive, model, session_id):
    """Produce a Socratic response, preferring Claude and falling back to the
    deterministic template engine.

    SymPy's `engine_result` is a trusted REFERENCE in both paths: where it has a
    verified result Claude is asked to stay consistent with it, but Claude may
    reason and compute on its own where SymPy is silent (see
    prompts.build_socratic_system). Returns the SocraticEngine response shape
    plus an `ai_provider` field so the UI can show who answered.
    """
    base = SocraticEngine.generate_socratic_response(
        engine_result, hint_level=hint_level, adaptive_context=adaptive
    )
    base["ai_provider"] = "template"

    if claude_service.available():
        try:
            system = prompts.build_socratic_system(engine_result, hint_level, adaptive)
            user = (f"Produce the level {hint_level} hint now for the problem "
                    f"\"{engine_result.get('original', '')}\".")
            text = claude_service.complete(
                system=system,
                messages=[{"role": "user", "content": user}],
                model=model,
                session_id=session_id,
            )
            base["messages"] = [{
                "role": "tutor",
                "content": text,
                "hint_level": hint_level,
            }]
            base["ai_provider"] = "claude:" + config.valid_model(
                model or config.CLAUDE_DEFAULT_MODEL
            )
        except ClaudeError as e:
            # Keep the template messages already in `base`; note why we fell back.
            base["ai_provider"] = "template"
            base["ai_fallback_reason"] = str(e)

    return base


@app.post("/analyze")
def analyze_math(request: MathRequest):
    """
    ALMAS Pipeline:
      Sprint Agent  →  parse & classify the request
      Control Agent  →  compile blending instructions
      Policy Engine  →  validate against guardrails
      Developer Agent  →  run neuro-symbolic engine
      Peer Agent  →  generate Socratic response (never reveal answer directly)
    """
    session_id = request.session_id or str(uuid4())

    # ── Sprint Agent: validate input ──
    policy_result = PolicyEngine.evaluate(request.expression)
    if not policy_result.allowed:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Policy violation detected",
                "violations": policy_result.violations,
                "penalty_score": policy_result.penalty_score,
            },
        )

    # ── Control Agent: compile blending instructions ──
    context = BlendingInstructions.compile(
        request.expression, session_id, request.action
    )

    # ── Developer Agent: run neuro-symbolic engine ──
    engine_result = NeuroSymbolicEngine.solve_with_steps(request.expression)

    # ── Peer Agent: generate Socratic response (hint level 0) ──
    # Prefer Claude; fall back to templates. SymPy stays the ground truth.
    adaptive = memory.get_adaptive_context(session_id)
    socratic = generate_socratic(
        engine_result, hint_level=0, adaptive=adaptive,
        model=request.model, session_id=session_id,
    )

    # Record interaction in experience memory
    memory.record_interaction(session_id, request.expression, 0, False)
    for msg in socratic["messages"]:
        memory.add_message(session_id, SocraticMessage(
            role=msg["role"],
            content=msg["content"],
            hint_level=0,
        ))

    return {
        "session_id": session_id,
        "original": request.expression,
        "latex": engine_result.get("latex", ""),
        "classification": engine_result.get("classification", {}),
        "socratic": socratic,
        "blending_context": {
            "strategic_intent": context["strategic_intent"],
            "architectural_boundaries": {
                "socratic_constraint_active": True,
                "direct_answer_forbidden": True,
            },
        },
        "policy_status": {
            "checked": True,
            "allowed": True,
            "active_policies": len(PolicyEngine.POLICIES),
        },
        "verification_status": engine_result.get("verification_status", "pending"),
        "ai_provider": socratic.get("ai_provider", "template"),
        # Legacy compatibility
        "solution": None,
        "steps": [m["content"] for m in socratic["messages"] if m["role"] == "tutor"],
        "type": engine_result.get("classification", {}).get("type", "unknown"),
    }


@app.post("/hint")
def get_next_hint(request: MathRequest):
    """
    Progressive hint endpoint — each call reveals one more level
    of Socratic guidance. Implements the Reflection Pattern.
    """
    session_id = request.session_id or str(uuid4())
    session = memory.get_or_create_session(session_id)

    # Determine current hint level
    current_level = session["hint_levels_used"].get(request.expression, 0)
    next_level = min(current_level + 1, 4)

    # Policy check
    policy_result = PolicyEngine.evaluate(request.expression)
    if not policy_result.allowed:
        raise HTTPException(status_code=400, detail="Policy violation")

    # Run engine
    engine_result = NeuroSymbolicEngine.solve_with_steps(request.expression)
    adaptive = memory.get_adaptive_context(session_id)
    socratic = generate_socratic(
        engine_result, hint_level=next_level, adaptive=adaptive,
        model=request.model, session_id=session_id,
    )

    # Record
    memory.record_interaction(session_id, request.expression, next_level, False)
    for msg in socratic["messages"]:
        memory.add_message(session_id, SocraticMessage(
            role=msg["role"], content=msg["content"], hint_level=next_level,
        ))

    return {
        "session_id": session_id,
        "hint_level": next_level,
        "socratic": socratic,
        "verification_status": engine_result.get("verification_status"),
        "ai_provider": socratic.get("ai_provider", "template"),
    }


#  ═══════════════════════════════════════════════════════════════════════
#  EXAM — AI-generated question bank covering all knowledge points
#  ═══════════════════════════════════════════════════════════════════════

# Valid JSON string escapes; any other backslash (common in raw LaTeX like
# \times, \quad, \frac) is illegal JSON and makes json.loads throw — which used
# to silently drop perfectly good (often the HARDEST) generated questions.
_VALID_JSON_ESCAPE = set('"\\/bfnrtu')


def _repair_json_backslashes(t: str) -> str:
    """Double any backslash that isn't a valid JSON escape, so LaTeX-laden model
    output (\\times, \\quad, \\frac …) parses instead of being discarded."""
    out = []
    i, n = 0, len(t)
    while i < n:
        c = t[i]
        if c == "\\" and i + 1 < n and t[i + 1] not in _VALID_JSON_ESCAPE:
            out.append("\\\\")          # lone backslash → escaped backslash
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _parse_json_array(text: str):
    """Pull a JSON array out of a model response (tolerate fences / prose / raw
    LaTeX backslashes)."""
    if not text:
        return None
    t = text.strip()
    t = _re.sub(r"^```(?:json)?", "", t).strip()
    t = _re.sub(r"```$", "", t).strip()
    start, end = t.find("["), t.rfind("]")
    if start != -1 and end > start:
        t = t[start:end + 1]
    try:
        data = _json.loads(t)
        return data if isinstance(data, list) else None
    except Exception:
        pass
    try:                                # retry after repairing invalid escapes
        data = _json.loads(_repair_json_backslashes(t))
        return data if isinstance(data, list) else None
    except Exception:
        return None


def _ai_questions_for_dimension(dim: str, grade, session_id: str):
    """Ask Claude for one question per knowledge-point tag in `dim`, as JSON.

    Each question keeps its knowledge point as the PRIMARY tag (so /exam/generate
    still guarantees 25/25 coverage), and additionally carries — drawn from / grown
    into the live tags.db vocabulary — one or more 逻辑思维类型 (logic) tags plus an
    open-ended difficulty (the v2.0 core fields). Any logic type the model proposes
    when nothing fits is ADDED to the store (self-evolving loop). [] on failure."""
    subdims = exam.CATALOGUE[dim]
    other_dim = exam.DIM_METHOD if dim == exam.DIM_CORE else exam.DIM_CORE
    other_tags = [t["tag"] for t in exam.all_tags() if t["dimension"] == other_dim]
    l_tags = [{"name": t["name"], "move": (t.get("meta") or {}).get("move"),
               "flaw": (t.get("meta") or {}).get("flaw")}
              for t in tags.list_tags(kind=tags.KIND_LOGIC)]
    system = prompts.build_exam_prompt(dim, subdims, other_dim, other_tags,
                                       logic_tags=l_tags)
    arr = None
    for attempt in range(3):       # retry transient timeouts / truncated-JSON parse misses
        try:
            text = claude_service.complete(
                system=system,
                messages=[{"role": "user", "content": "请生成题目，只输出 JSON 数组。"}],
                session_id=f"{session_id}:{dim}", max_tokens=6000,
                temperature=0.7 + 0.1 * attempt,
                timeout=180,        # one big batch (many questions) needs far longer than chat
            )
        except ClaudeError:
            return []
        arr = _parse_json_array(text)
        if arr:
            break
    if not arr:
        return []

    valid = {t["tag"] for t in exam.all_tags() if t["dimension"] == dim}
    valid_other = {t["tag"] for t in exam.all_tags() if t["dimension"] == other_dim}
    known_l = {t["name"] for t in l_tags}
    out = []
    for item in arr:
        if not isinstance(item, dict):
            continue
        ptag = (item.get("primary_tag") or "").strip()
        if ptag not in valid:
            continue

        # Self-evolving step: register any NEW logic/knowledge tags proposed, so a
        # freshly-coined deep logic type can be attached to the very question below.
        added_logic: List[str] = []
        for nt in (item.get("new_tags") or []):
            if not isinstance(nt, dict):
                continue
            nm = (nt.get("name") or "").strip()
            kind = (nt.get("kind") or "").strip()
            if not nm or kind not in (tags.KIND_LOGIC, tags.KIND_KNOWLEDGE):
                continue
            tags.add_tag(nm, kind, description=(nt.get("reason") or "").strip() or None,
                         source="ai")
            if kind == tags.KIND_LOGIC:
                added_logic.append(nm); known_l.add(nm)

        # Knowledge point stays PRIMARY (coverage contract); cross-mark the other
        # knowledge dimension; then attach the logic-thinking type(s) + difficulty.
        qtags = [{"dimension": dim, "subdimension": exam.tag_subdimension(ptag) or "",
                  "tag": ptag, "primary": True}]
        tags.bump_usage(ptag)
        for ot in (item.get("also_tags") or []):
            ot = (ot or "").strip()
            if ot in valid_other:
                qtags.append({"dimension": other_dim,
                              "subdimension": exam.tag_subdimension(ot) or "",
                              "tag": ot, "primary": False})
                tags.bump_usage(ot)
        chosen_logic = [t for t in (item.get("logic_tags") or []) if t in known_l]
        for nm in added_logic:
            if nm not in chosen_logic:
                chosen_logic.append(nm)
        for nm in chosen_logic:
            qtags.append(_question_tag_row(nm, primary=False))
            tags.bump_usage(nm)

        diff = item.get("difficulty")
        try:                                # open-ended ladder: floor only, no cap
            diff = max(exam.DIFFICULTY_MIN, int(diff)) if diff is not None else None
        except (ValueError, TypeError):
            diff = None

        out.append({
            "statement": (item.get("statement") or "").strip(),
            "latex": (item.get("latex") or "").strip(),
            "answer": (item.get("answer") or "").strip(),
            "grade": grade,
            "difficulty": diff,
            "source": "ai",
            "tags": qtags,
        })
    return out


@app.post("/exam/generate")
def exam_generate(grade: Optional[int] = None):
    """Generate a fresh set of questions covering EVERY knowledge-point tag
    across both dimensions, save them to the bank, and return them.

    AI (Claude) writes the questions; any tag the AI misses (or all of them, if
    the gateway is down) is filled deterministically from the template bank so
    coverage is always complete.
    """
    use_ai = claude_service.available()
    generated = []
    covered_primary = set()

    if use_ai:
        for dim in (exam.DIM_CORE, exam.DIM_METHOD):
            for q in _ai_questions_for_dimension(dim, grade, "exam-gen"):
                for t in q["tags"]:
                    if t.get("primary"):
                        covered_primary.add(t["tag"])
                generated.append(q)

    # Fill any uncovered tag with a template question → guaranteed full coverage.
    for entry in exam.all_tags():
        if entry["tag"] not in covered_primary:
            tq = exam.template_question(entry["tag"])
            tq["grade"] = grade
            generated.append(tq)
            covered_primary.add(entry["tag"])

    saved = []
    for q in generated:
        qid = exam.save_question(q)
        q = dict(q)
        q["id"] = qid
        saved.append(q)

    return {
        "provider": "claude" if use_ai else "template",
        "generated": len(saved),
        "questions": saved,
        "coverage": exam.coverage(),
        "bank_size": exam.bank_size(),
    }


@app.get("/exam/catalogue")
def exam_catalogue():
    """The two-dimension taxonomy + which tags currently have questions."""
    return {
        "catalogue": exam.CATALOGUE,
        "coverage": exam.coverage(),
        "bank_size": exam.bank_size(),
    }


@app.get("/exam/questions")
def exam_questions():
    """All questions currently in the bank (most recent first)."""
    return {"questions": exam.list_questions(), "bank_size": exam.bank_size()}


@app.get("/exam/by-tag")
def exam_by_tag(tag: str, dimension: Optional[str] = None):
    """Immediate lookup of every question carrying a given type/tag."""
    return {
        "tag": tag,
        "dimension": dimension,
        "questions": exam.find_by_tag(tag, dimension),
    }


# ── Dynamic tag vocabulary (tags.py / tags.db) ──────────────────────────────
# The evolving tag set: AI/user may ADD fitting tags and REMOVE any tag (incl.
# the seeded lesson/README knowledge points). Source of truth once seeded.

class TagCreate(BaseModel):
    name: str
    kind: str = tags.KIND_LOGIC
    parent: Optional[str] = None
    description: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    source: str = "user"


@app.get("/tags")
def tags_list(kind: Optional[str] = None, include_inactive: bool = False):
    """The dynamic tag vocabulary. Optional `kind` filter
    ('knowledge'|'logic'|…); `include_inactive=1` also returns soft-deleted."""
    return {
        "tags": tags.list_tags(kind=kind, include_inactive=include_inactive),
        "count": tags.count(),
    }


@app.get("/tags/catalogue")
def tags_catalogue(include_inactive: bool = False):
    """Grouped view kind → parent → [tags] — the dynamic replacement for the
    hard-coded exam catalogues."""
    return {"catalogue": tags.catalogue(include_inactive=include_inactive),
            "count": tags.count()}


@app.post("/tags")
def tags_add(body: TagCreate):
    """Add (or re-activate) a tag — how the AI/user grows the vocabulary with a
    fitting tag. Idempotent by name."""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="tag name is required")
    tag = tags.add_tag(name, body.kind, parent=body.parent,
                       description=body.description, meta=body.meta, source=body.source)
    return {"tag": tag}


@app.delete("/tags/{name}")
def tags_delete(name: str, hard: bool = False):
    """Remove a tag — soft by default (active=0), `hard=1` deletes the row.
    Nothing is protected: the seeded lesson/README knowledge points can go too."""
    ok = tags.remove_tag(name, hard=hard)
    if not ok:
        raise HTTPException(status_code=404, detail=f"tag not found or already inactive: {name}")
    return {"removed": name, "hard": hard}


# ── Logic-flaw diagnosis (diagnosis.py) ─────────────────────────────────────

@app.get("/diagnosis/self")
def diagnosis_self(limit: Optional[int] = None):
    """AI-self logic profile: logic types where the tutor's OWN multi-path
    consensus diverges most (its own shaky reasoning). Goal 6 self-diagnosis seed."""
    return diagnosis.self_profile(limit=limit)


@app.get("/diagnosis/{session_id}")
def diagnosis_student(session_id: str):
    """Per-student logic-flaw profile: per-tag success + ranked weak logic types,
    plus a suggested focus (the weakest) for adaptive 出题 (goals 5/2)."""
    prof = diagnosis.student_profile(session_id)
    prof["suggested_focus"] = prof["weak_logic"][0]["tag"] if prof["weak_logic"] else None
    return prof


# ── Personal workspace (校对屏 草稿库) ───────────────────────────────────────

def _work_owner(user: Optional[Dict[str, Any]], session_id: Optional[str]) -> str:
    """Scope a draft to its owner: the signed-in username, else the anonymous
    session id, else a generic anon bucket. Mirrors the草图's 「个人 tmp 数据库」."""
    if user and user.get("username"):
        return f"user:{user['username']}"
    if session_id and session_id.strip():
        return f"sess:{session_id.strip()}"
    return "anon"


@app.post("/work/save")
def work_save(req: WorkSaveRequest, authorization: Optional[str] = Header(default=None)):
    """Save a draft from the 校对屏: 「存草稿」(status=tmp) or 「提交」(status=final).
    Returns the stored draft so the UI can keep its id and 续作 (reopen + continue)."""
    owner = _work_owner(optional_user(authorization), req.session_id)
    draft = workspace.save_draft(
        owner,
        question_id=req.question_id,
        filename=(req.filename or "").strip() or None,
        content_md=req.content_md or "",
        render_mode=req.render_mode,
        status=req.status,
        draft_id=req.draft_id,
    )
    return draft


@app.get("/work")
def work_list(session: Optional[str] = None, question_id: Optional[str] = None,
              authorization: Optional[str] = Header(default=None)):
    """List the caller's drafts (newest first), optionally scoped to one question —
    drives the 校对屏「我的草稿」list so a saved draft can be reopened."""
    owner = _work_owner(optional_user(authorization), session)
    return {"drafts": workspace.list_drafts(owner, question_id)}


@app.get("/work/{draft_id}")
def work_get(draft_id: str, session: Optional[str] = None,
             authorization: Optional[str] = Header(default=None)):
    """One draft by id, scoped to its owner."""
    owner = _work_owner(optional_user(authorization), session)
    draft = workspace.get_draft(draft_id, owner)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@app.delete("/work/{draft_id}")
def work_delete(draft_id: str, session: Optional[str] = None,
                authorization: Optional[str] = Header(default=None)):
    """Delete a draft the caller owns."""
    owner = _work_owner(optional_user(authorization), session)
    if not workspace.delete_draft(draft_id, owner):
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"deleted": draft_id}


# ── AI assistant (④ 助手屏): line-by-line analysis + per-line follow-up ───────

def _resolve_problem_text(problem: Optional[str], question_id: Optional[str]) -> str:
    """The problem text the assistant grounds on: prefer what the frontend sent
    (statement + latex), else reconstruct it from the bank by question_id."""
    text = (problem or "").strip()
    if text:
        return text
    if question_id:
        q = exam.get_question(question_id)
        if q:
            parts = [str(q.get("statement") or "").strip(), str(q.get("latex") or "").strip()]
            return "\n".join(p for p in parts if p)
    return ""


@app.post("/assistant/analyze")
def assistant_analyze(req: AssistantAnalyzeRequest):
    """Line-by-line analysis of the student's corrected work (校对屏 → 助手屏).
    Returns ``{lines:[{idx,content,analysis,has_issue,manim}], summary, provider}``;
    correct lines come back with an empty analysis (blank right column). Always 200 —
    ``provider`` is ``template`` when Claude is unavailable so the screen still works."""
    problem_text = _resolve_problem_text(req.problem, req.question_id)
    return assistant.analyze(
        problem_text, req.student_work_md,
        session_id=req.session_id or "assistant",
        model=req.model, render_mode=req.render_mode,
    )


@app.post("/assistant/ask")
def assistant_ask(req: AssistantAskRequest):
    """Per-line follow-up chat for the 助手屏. Grounds the reply in the clicked line
    (``focus`` = {idx, content, analysis}) plus the problem. Always 200 with a
    ``provider`` so the shared chat control can fall back gracefully."""
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Empty message")
    problem_text = _resolve_problem_text(req.problem, req.question_id)
    return assistant.ask(
        message, problem=problem_text, focus=req.focus,
        history=req.history, render_mode=req.render_mode,
        allow_special=req.allow_special, model=req.model,
        session_id=req.session_id or "assistant",
    )


#  ═══════════════════════════════════════════════════════════════════════
#  AUTH — sign up / sign in / sign out / current user (SQLite-backed)
#  ═══════════════════════════════════════════════════════════════════════

@app.post("/auth/signup")
def auth_signup(req: SignUpRequest):
    """Create a new account and return {user, token}. Token goes in the
    Authorization header on later requests."""
    try:
        result = auth.sign_up(req.username, req.password, req.email)
    except auth.AuthError as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    return result


@app.post("/auth/signin")
def auth_signin(req: SignInRequest):
    """Validate credentials and return {user, token}."""
    try:
        result = auth.sign_in(req.username, req.password)
    except auth.AuthError as e:
        raise HTTPException(status_code=e.code, detail=e.message)
    return result


@app.post("/auth/signout")
def auth_signout(authorization: Optional[str] = Header(default=None)):
    """Invalidate the caller's session token."""
    auth.sign_out(_bearer_token(authorization))
    return {"ok": True}


@app.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(default=None)):
    """Return the current user for a valid session token, else 401."""
    user = auth.get_user_by_token(_bearer_token(authorization))
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    return {"user": user}


@app.get("/claude/models")
def claude_models():
    """Models for the UI dropdown + whether the gateway is actually usable.
    The frontend shows the list regardless; `available` tells it whether
    answers will come from Claude or fall back to the template engine."""
    return {
        "available": claude_service.available(),
        "default_model": config.CLAUDE_DEFAULT_MODEL,
        "models": config.CLAUDE_MODELS,
        "status": claude_service.status(),
    }


@app.post("/claude/chat")
def claude_chat(request: ChatRequest):
    """Free-form tutor chat (the AI Response chat box).

    Grounded in SymPy: if an `expression` is supplied we solve it first and
    pass the verified result to Claude as ground truth. Always returns 200 with
    `provider` so the frontend can fall back to its local heuristic when Claude
    is unavailable rather than showing an error.
    """
    session_id = request.session_id or str(uuid4())
    user_message = (request.message or "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message")

    # Ground the chat in verified math when we have a problem in context.
    engine_result = None
    if request.expression:
        policy_result = PolicyEngine.evaluate(request.expression)
        if policy_result.allowed:
            engine_result = NeuroSymbolicEngine.solve_with_steps(request.expression)

    if not claude_service.available():
        return {
            "session_id": session_id,
            "reply": None,
            "provider": "unavailable",
            "available": False,
            "reason": "Claude gateway not configured." if not config.is_configured()
                      else "Claude temporarily unavailable (circuit breaker).",
        }

    try:
        system = prompts.build_chat_system(request.expression or "", engine_result,
                                           allow_special=request.allow_special)
        messages = prompts.to_messages(request.history or [], user_message)
        reply = claude_service.complete(
            system=system, messages=messages,
            model=request.model, session_id=session_id,
        )
        model_id = config.valid_model(request.model or config.CLAUDE_DEFAULT_MODEL)
        # Persist the exchange in experience memory.
        memory.add_message(session_id, SocraticMessage(role="user", content=user_message))
        memory.add_message(session_id, SocraticMessage(role="tutor", content=reply))
        return {
            "session_id": session_id,
            "reply": reply,
            "provider": "claude:" + model_id,
            "available": True,
        }
    except ClaudeError as e:
        return {
            "session_id": session_id,
            "reply": None,
            "provider": "error",
            "available": False,
            "reason": str(e),
        }


@app.get("/session/{session_id}")
def get_session(session_id: str):
    """Retrieve session history and experience memory."""
    session = memory.get_or_create_session(session_id)
    return {
        "session": session,
        "adaptive_context": memory.get_adaptive_context(session_id),
    }


@app.get("/architecture")
def get_architecture():
    """Data Manager — return the architecture as a JSON metadata tree."""
    return build_architecture_tree()


@app.get("/policies")
def get_policies():
    """Return all active policy guardrails."""
    return {
        "framework": "SEPGA (Self-Evolving, Policy-Governed Agentic Automation)",
        "policies": PolicyEngine.get_active_policies(),
        "penalty_threshold": PolicyEngine.PENALTY_THRESHOLD,
        "constraint": "Socratic methodology — direct answers are architecturally forbidden",
    }


def _check_student_answer(expression: str, answer: str, session_id: Optional[str] = None,
                          model: Optional[str] = None) -> Dict[str, Any]:
    """Grade a student's answer. Correctness now comes from CONSENSUS, not a CAS:
    the LLM solves the problem several times independently and we keep the answer
    the derivations AGREE on (see reasoner.py). This is the source of truth.

    SymPy is demoted to a fallback for when the gateway is down or the independent
    paths disagree — never the sole arbiter — so word problems / geometry /
    statistics (which SymPy silently declines) are now gradable, while simple
    algebra is still gradable offline.

    Returns {"correct": Optional[bool], "judged_by": str|None, "reason": str|None}
    plus optional "ground_truth"/"agreement"/"votes_label"; correct=None =
    undetermined (caller should not guess).
    """
    if not answer or not answer.strip():
        return {"correct": None, "judged_by": None, "reason": None}

    # ── Primary judge: multi-path LLM consensus ──
    cg = reasoner_engine.grade(expression, answer, model=model, session_id=session_id)
    if cg.get("correct") is not None:
        out = {"correct": cg["correct"], "judged_by": cg["judged_by"],
               "reason": cg.get("reason")}
        for k in ("ground_truth", "agreement", "votes_label"):
            if cg.get(k) is not None:
                out[k] = cg[k]
        return out

    # ── Fallback: non-authoritative SymPy cross-check (offline / disagreement) ──
    # Only trusted where SymPy is confident; used because consensus was unavailable
    # (gateway down) or the independent paths failed to agree. The retired SymPy
    # grader lives in app.legacy now; we inject the rendering engine's solver so the
    # legacy module stays free of any import back into main.
    sv = sympy_grader.sympy_grade(
        expression, answer, NeuroSymbolicEngine.solve_with_steps
    )
    if sv is not None:
        return {"correct": sv, "judged_by": "sympy-fallback", "reason": None}

    return {"correct": None, "judged_by": cg.get("judged_by"),
            "reason": cg.get("reason")}


def _record_diagnosis(session_id: Optional[str], question_id: Optional[str],
                      is_correct: Optional[bool], agreement: Optional[float]) -> None:
    """Feed a graded attempt into logic-flaw diagnosis: per the question's tags,
    record the STUDENT outcome (per session) and the AI-SELF consensus signal
    (global). No-op without a question_id (we need the question's tags)."""
    if not question_id:
        return
    q = exam.get_question(question_id)
    if not q:
        return
    for t in q.get("tags", []):
        tag, dim = t.get("tag"), t.get("dimension")
        if not tag:
            continue
        kind = tags.KIND_LOGIC if dim == exam.DIM_LOGIC else tags.KIND_KNOWLEDGE
        if session_id and is_correct is not None:
            diagnosis.record_student_outcome(session_id, tag, kind, bool(is_correct))
        if kind == tags.KIND_LOGIC and agreement is not None:
            diagnosis.record_self_signal(tag, kind, agreement)


@app.post("/verify")
def verify_expression(request: MathRequest):
    """
    Standalone verification endpoint — useful for checking student work.

    If the student supplies their own `answer` (plus a `session_id`), the answer
    is graded by MULTI-PATH LLM CONSENSUS — several independent derivations must
    agree — with SymPy kept only as an offline fallback (see
    `_check_student_answer`). The verdict is recorded in experience memory as a
    genuine "solved / not solved" signal, which is what lets `success_rate` and
    adaptive difficulty actually move over time. The response carries `judged_by`
    (e.g. "consensus(3/3)") and `agreement` so the UI/caller knows how it graded.
    """
    policy_result = PolicyEngine.evaluate(request.expression)
    if not policy_result.allowed:
        raise HTTPException(status_code=400, detail="Policy violation")

    result = NeuroSymbolicEngine.solve_with_steps(request.expression)
    response: Dict[str, Any] = {
        "original": request.expression,
        "classification": result["classification"],
        "verified_steps": result["verified_steps"],
        "verification_status": result["verification_status"],
        "latex": result["latex"],
    }

    # ── Grade the student's own answer + emit the experience-memory signal ──
    if request.answer is not None and request.answer.strip():
        verdict = _check_student_answer(
            request.expression, request.answer, request.session_id, request.model
        )
        is_correct = verdict["correct"]
        response["answer_checked"] = is_correct is not None
        response["answer_correct"] = is_correct
        response["judged_by"] = verdict["judged_by"]
        if verdict.get("reason"):
            response["judge_reason"] = verdict["reason"]
        # Expose the consensus trace: the agreed answer + how many paths agreed.
        if verdict.get("ground_truth") is not None:
            response["ground_truth"] = verdict["ground_truth"]
        if verdict.get("agreement") is not None:
            response["agreement"] = verdict["agreement"]
        if verdict.get("votes_label"):
            response["votes_label"] = verdict["votes_label"]
        if request.session_id and is_correct is not None:
            session = memory.get_or_create_session(request.session_id)
            # Record success at however many hints the student had reached.
            hint_level = session["hint_levels_used"].get(request.expression, 0)
            memory.record_interaction(
                request.session_id, request.expression, hint_level, bool(is_correct),
            )
            response["adaptive_context"] = memory.get_adaptive_context(request.session_id)
        # Logic-flaw diagnosis: attribute this outcome to the question's logic
        # types (student profile) + record the AI's own consensus health (self).
        _record_diagnosis(request.session_id, request.question_id, is_correct,
                          verdict.get("agreement"))

    return response


# ═══════════════════════════════════════════════════════════════════════
#  MATH-TO-MANIM ANIMATION ENGINE
#  (inspired by github.com/HarleyCoops/Math-To-Manim)
# ═══════════════════════════════════════════════════════════════════════
#
# Math-To-Manim turns a math prompt into an animated Manim scene. We mirror
# that idea WITHOUT the heavy LLM + Manim render pipeline: the SymPy solver
# produces verified solution steps, and a deterministic template converts them
# into (a) ready-to-render Manim CE Python code and (b) a lightweight
# "storyboard" the browser animates frame-by-frame with MathJax.

class ManimAnimator:
    """Template-based Manim scene generator (no LLM, no rendering)."""

    @staticmethod
    def _py(latex_str: Optional[str]) -> str:
        """Escape a LaTeX string for embedding in generated (non-raw) Python."""
        s = latex_str or ""
        return s.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _plain(text: Optional[str]) -> str:
        """Strip $-delimiters so step descriptions read as plain captions."""
        return (text or "").replace("$", "").strip()

    @staticmethod
    def _is_ascii(s: Optional[str]) -> bool:
        """True when text is pure ASCII — safe for MathTex/Tex. LaTeX on the base
        install CANNOT typeset Chinese/non-ASCII (the render crashes), so such content
        must go through Text()/Pango instead."""
        try:
            (s or "").encode("ascii")
            return True
        except UnicodeEncodeError:
            return False

    @classmethod
    def _formula(cls, var: str, content: str) -> "tuple[str, bool]":
        """Assignment line for a formula mobject + whether it's a Tex-type (MathTex).
        ASCII math → MathTex; anything with CJK → Text (so a Chinese/unsolvable
        expression falling back to the raw problem text still renders, not crashes)."""
        if cls._is_ascii(content):
            return f'{var} = MathTex("{cls._py(content)}").scale(1.4)', True
        return f'{var} = Text("{cls._py(content)}", font_size=40)', False

    @classmethod
    def build(cls, expr_str: str) -> Dict[str, Any]:
        engine = NeuroSymbolicEngine.solve_with_steps(expr_str)
        steps = engine.get("verified_steps", [])
        eq_latex = engine.get("latex") or expr_str
        solution = engine.get("solution")

        # ── Storyboard: one frame per solution state (for the browser) ──
        storyboard: List[Dict[str, Any]] = [{
            "index": 0,
            "title": "The problem",
            "latex": eq_latex,
            "caption": f"Let's solve {expr_str}",
        }]
        for s in steps:
            result_latex = s.get("result_latex") or ""
            if not result_latex:
                continue
            storyboard.append({
                "index": s.get("step"),
                "title": s.get("action", ""),
                "latex": result_latex,
                "caption": cls._plain(s.get("description", "")),
            })

        return {
            "expression": expr_str,
            "latex": eq_latex,
            "solution": solution,
            "scene_name": "SolveScene",
            "storyboard": storyboard,
            "manim_code": cls._render_code(expr_str, eq_latex, steps),
            "verification_status": engine.get("verification_status", "pending"),
        }

    @classmethod
    def _render_code(cls, expr_str: str, eq_latex: str, steps: List[Dict]) -> str:
        """Emit a self-contained Manim CE Scene that animates the solution.

        Text vs. formula matters: MathTex/Tex go through LaTeX (no CJK on the base
        install), so the title/captions — which may be Chinese — use Text(), and the
        equation uses MathTex only when it is pure ASCII (else Text()). This keeps a
        Chinese word-problem (whose ``eq_latex`` falls back to the raw problem text)
        renderable instead of crashing the LaTeX pass."""
        py = cls._py
        eq_line, eq_is_tex = cls._formula("eq", eq_latex)
        # Title via Text (Pango) — "Solving: <expr>" may include Chinese.
        L: List[str] = [
            "from manim import *",
            "",
            "",
            "class SolveScene(Scene):",
            '    """Auto-generated by the Math-To-Manim-style template engine."""',
            "",
            "    def construct(self):",
            f'        title = Text("Solving:  {py(expr_str)}", font_size=40).to_edge(UP)',
            "        self.play(Write(title))",
            "        self.wait(0.5)",
            "",
            "        # Starting equation",
            f'        {eq_line}',
            "        self.play(Write(eq))",
            "        self.wait(1)",
        ]

        for s in steps:
            result_latex = s.get("result_latex")
            if not result_latex:
                continue
            action = py(s.get("action", ""))
            step_line, step_is_tex = cls._formula("step_eq", result_latex)
            # TransformMatchingTex needs BOTH sides to be Tex-type; fall back to a
            # ReplacementTransform (works for any mobjects, and — unlike plain Transform
            # — swaps eq off-screen for step_eq so `eq = step_eq` below stays correct)
            # whenever either side is a Text (CJK) mobject.
            morph = ("TransformMatchingTex(eq, step_eq)"
                     if eq_is_tex and step_is_tex else "ReplacementTransform(eq, step_eq)")
            L += [
                "",
                f'        # Step {s.get("step")}: {action}',
                f'        caption = Text("{action}", font_size=32).to_edge(DOWN)',
                f'        {step_line}',
                "        self.play(",
                f'            {morph},',
                "            FadeIn(caption, shift=UP),",
                "        )",
                "        self.wait(1.2)",
                "        self.play(FadeOut(caption))",
                "        eq = step_eq",
            ]
            eq_is_tex = step_is_tex

        L += [
            "",
            "        # Highlight the final result",
            "        box = SurroundingRectangle(eq, color=YELLOW, buff=0.2)",
            "        self.play(Create(box))",
            "        self.wait(2)",
        ]
        return "\n".join(L)


@app.post("/animate")
def animate_solution(request: MathRequest):
    """
    Math-To-Manim-style endpoint.

    Takes the expression typed in "Solve with Voice or Text" and returns:
      • storyboard  — solution frames for the in-browser animated walkthrough
      • manim_code  — ready-to-render Manim CE Python (paste into a .py & run
                      `manim -pql scene.py SolveScene` if Manim is installed)
    """
    policy_result = PolicyEngine.evaluate(request.expression)
    if not policy_result.allowed:
        raise HTTPException(
            status_code=400,
            detail={"message": "Policy violation", "violations": policy_result.violations},
        )
    return ManimAnimator.build(request.expression)


@app.post("/manim/render")
async def manim_render_endpoint(req: ManimRenderRequest):
    """Real Manim render (v0.4.5b) with graceful degradation.

    Renders a ``<manim>`` block to an actual MP4 when the server has Manim CE +
    ffmpeg; otherwise (or on render failure) returns ``status != "ok"`` plus the
    browser **storyboard** so the frontend animates in-page. Always 200 — the
    ``<manim>`` affordance never errors out, per the acceptance rule "无 Manim 时自动
    回落且不报错"."""
    expr = (req.expression or "").strip()
    if expr:
        policy = PolicyEngine.evaluate(expr)
        if not policy.allowed:
            raise HTTPException(
                status_code=400,
                detail={"message": "Policy violation", "violations": policy.violations},
            )

    # Template storyboard + template Manim code (SymPy-driven) — the always-available
    # fallback and the code we hand to the renderer when AI generation is off.
    board = ManimAnimator.build(expr) if expr else {"storyboard": [], "manim_code": ""}

    # Rendering shells out (subprocess) and can take many seconds; keep the event
    # loop free by offloading to a worker thread.
    result = await run_in_threadpool(
        manim_render.render,
        manim_code=req.manim_code,
        spec=(req.spec or ""),
        expression=expr,
        template_code=board.get("manim_code"),
        session_id=req.session_id or "manim",
        model=req.model,
    )

    # Attach the storyboard + expression so the UI can degrade to in-page frames.
    result.setdefault("storyboard", board.get("storyboard", []))
    result.setdefault("expression", expr)
    if not result.get("manim_code"):
        result["manim_code"] = board.get("manim_code", "")
    return result


# ═══════════════════════════════════════════════════════════════════════
#  SYMPY-POWERED PLOTTING  (the visual payoff for the "Solve with SymPy" path)
# ═══════════════════════════════════════════════════════════════════════

class SymPyPlotter:
    """Build graph data with SymPy so the browser can animate the curve.

    SymPy does the math — `lambdify` turns the expression into a numeric
    function we sample over a window, and `solve` gives exact roots that mark
    the solution(s). No matplotlib / image rendering; we return raw points and
    the frontend traces them on a <canvas>.
    """

    SAMPLES = 140

    @classmethod
    def build(cls, expr_str: str) -> Dict[str, Any]:
        try:
            # Turn "lhs = rhs" into f = lhs - rhs, so its roots ARE the solutions.
            if "=" in expr_str:
                parts = expr_str.split("=")
                lhs = safe_parse(parts[0])
                rhs = safe_parse(parts[1])
                expr = lhs - rhs
                display_latex = latex(Eq(lhs, rhs))
                is_equation = True
            else:
                expr = safe_parse(expr_str)
                display_latex = latex(expr)
                is_equation = False
        except Exception as exc:
            return {"plottable": False, "expression": expr_str,
                    "reason": f"Could not parse the expression ({exc})."}

        free = list(expr.free_symbols)
        if len(free) != 1:
            return {
                "plottable": False,
                "expression": expr_str,
                "latex": display_latex,
                "reason": "Need exactly one variable to draw a 2-D curve.",
            }

        var = free[0]
        f = lambdify(var, expr, modules=["math"])

        # Exact roots (real only) — these drive the view window and the markers.
        roots: List[float] = []
        try:
            for s in solve(Eq(expr, 0), var):
                v = complex(s.evalf())
                if abs(v.imag) < 1e-9:
                    roots.append(float(v.real))
        except Exception:
            pass

        # Centre the x-window on the roots when we have them; else a sane default.
        if roots:
            lo, hi = min(roots), max(roots)
            pad = max(2.0, (hi - lo) * 0.8 + 2.0)
            x_min, x_max = lo - pad, hi + pad
        else:
            x_min, x_max = -10.0, 10.0

        points: List[List[float]] = []
        n = cls.SAMPLES
        for i in range(n + 1):
            x = x_min + (x_max - x_min) * i / n
            try:
                y = f(x)
                if isinstance(y, complex):
                    continue
                y = float(y)
                if y != y or y in (float("inf"), float("-inf")) or abs(y) > 1e6:
                    continue
                points.append([round(x, 4), round(y, 4)])
            except Exception:
                continue

        return {
            "plottable": len(points) > 1,
            "expression": expr_str,
            "latex": display_latex,
            "function_latex": "y = " + latex(expr),
            "variable": str(var),
            "is_equation": is_equation,
            "x_range": [round(x_min, 4), round(x_max, 4)],
            "points": points,
            "roots": sorted({round(r, 6) for r in roots}),
        }


@app.post("/plot")
def plot_solution(request: MathRequest):
    """SymPy-powered plot endpoint.

    Returns curve data (computed with SymPy's `lambdify`) plus exact roots,
    so the "Solve with SymPy" choice can animate the graph of the expression
    with its solution(s) marked — SymPy doing the visualization math.
    """
    policy_result = PolicyEngine.evaluate(request.expression)
    if not policy_result.allowed:
        raise HTTPException(
            status_code=400,
            detail={"message": "Policy violation", "violations": policy_result.violations},
        )
    return SymPyPlotter.build(request.expression)


# Run from the backend/ directory:  uvicorn app.main:app --host 0.0.0.0 --port 8000
# (or `python -m app.main`). main.py is a package module now, so relative
# imports require it be launched as `app.main`, not as a bare script.
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
