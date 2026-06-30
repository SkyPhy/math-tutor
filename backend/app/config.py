"""
Configuration & secrets for the Claude integration.
=====================================================
The AI tutor talks to an **Anthropic-compatible gateway** (the gateway speaks
the Messages API at `{BASE_URL}/v1/messages`). All connection details are read
from environment variables, which are loaded from a local `.env` file at import
time. No secrets live in source.

Copy `.env.example` to `.env` and fill in:
  CLAUDE_BASE_URL   — gateway base, e.g. https://your-gateway.example.com
  CLAUDE_API_KEY    — your key
  CLAUDE_MODELS     — comma-separated `id|Label` pairs for the UI dropdown
  CLAUDE_DEFAULT_MODEL — which id is selected first

If CLAUDE_BASE_URL / CLAUDE_API_KEY are absent the service reports itself as
unavailable and the backend transparently falls back to the template-based
SocraticEngine, so the demo keeps working with no AI configured.
"""

import os
from pathlib import Path
from typing import List, Dict


# ── Minimal .env loader (no python-dotenv dependency) ──────────────────────
def _load_dotenv(path: Path) -> None:
    """Read KEY=VALUE lines from `path` into os.environ (without overriding
    variables already set in the real environment)."""
    if not path.exists():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        # A malformed .env should never crash the backend.
        pass


# config.py lives in backend/app/; the .env file sits at backend/.env, one
# level up. Secrets live ONLY in that file (gitignored) — never in source.
_load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _parse_models(spec: str) -> List[Dict[str, str]]:
    """Parse `id|Label,id2|Label2` into [{id, label}, ...].
    A bare `id` (no `|Label`) uses the id as its own label."""
    models: List[Dict[str, str]] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "|" in chunk:
            mid, label = chunk.split("|", 1)
        else:
            mid, label = chunk, chunk
        mid, label = mid.strip(), label.strip()
        if mid:
            models.append({"id": mid, "label": label or mid})
    return models


# ── Gateway connection ─────────────────────────────────────────────────────
# Base URL of the Anthropic-compatible gateway (no trailing slash, no /v1).
CLAUDE_BASE_URL: str = os.environ.get("CLAUDE_BASE_URL", "").rstrip("/")
CLAUDE_API_KEY: str = os.environ.get("CLAUDE_API_KEY", "")

# Auth header style. "x-api-key" (Anthropic standard) or "authorization"
# (sends `Authorization: Bearer <key>`).
CLAUDE_AUTH_HEADER: str = os.environ.get("CLAUDE_AUTH_HEADER", "x-api-key").lower()
CLAUDE_ANTHROPIC_VERSION: str = os.environ.get("CLAUDE_ANTHROPIC_VERSION", "2023-06-01")

# ── Models offered in the UI dropdown ──────────────────────────────────────
# Defaults reflect the models the user said they have access to. Override the
# ids in `.env` to match exactly what the gateway expects.
CLAUDE_MODELS: List[Dict[str, str]] = _parse_models(
    os.environ.get(
        "CLAUDE_MODELS",
        "claude-opus-4-8|Opus 4.8,"
        "claude-opus-4-6|Opus 4.6,"
        "claude-sonnet-4-6|Sonnet 4.6",
    )
)
CLAUDE_DEFAULT_MODEL: str = os.environ.get(
    "CLAUDE_DEFAULT_MODEL",
    CLAUDE_MODELS[0]["id"] if CLAUDE_MODELS else "claude-opus-4-8",
)

# ── Behaviour / safety knobs ───────────────────────────────────────────────
CLAUDE_TIMEOUT: float = float(os.environ.get("CLAUDE_TIMEOUT", "30"))
CLAUDE_MAX_TOKENS: int = int(os.environ.get("CLAUDE_MAX_TOKENS", "1024"))
CLAUDE_TEMPERATURE: float = float(os.environ.get("CLAUDE_TEMPERATURE", "0.4"))

# Circuit breaker: disable Claude after this many consecutive failures
# (auto-resets after CLAUDE_BREAKER_COOLDOWN seconds).
CLAUDE_BREAKER_THRESHOLD: int = int(os.environ.get("CLAUDE_BREAKER_THRESHOLD", "3"))
CLAUDE_BREAKER_COOLDOWN: float = float(os.environ.get("CLAUDE_BREAKER_COOLDOWN", "60"))

# Simple per-session rate limit (calls per hour). 0 disables the limit.
CLAUDE_RATE_PER_HOUR: int = int(os.environ.get("CLAUDE_RATE_PER_HOUR", "60"))


# ═══════════════════════════════════════════════════════════════════════════
#  HANDWRITING OCR — nex-n2-pro (OpenAI-compatible vision, SEPARATE endpoint)
# ═══════════════════════════════════════════════════════════════════════════
# The whiteboard PNG is sent to an OpenAI-compatible /chat/completions endpoint
# as an image_url; the model transcribes the handwritten math. This replaces the
# old local EasyOCR model. Configure these in `.env` (see .env.example).

# Base URL of the OCR gateway. May or may not include a trailing `/v1`; the
# client appends `/chat/completions` (adding `/v1` only if absent). No trailing
# slash needed. Example: https://your-ocr-gateway.example.com
NEX_OCR_BASE_URL: str = os.environ.get("NEX_OCR_BASE_URL", "").rstrip("/")
NEX_OCR_API_KEY: str = os.environ.get("NEX_OCR_API_KEY", "")
# Model id of the vision OCR model.
NEX_OCR_MODEL: str = os.environ.get("NEX_OCR_MODEL", "nex-n2-pro")
NEX_OCR_TIMEOUT: float = float(os.environ.get("NEX_OCR_TIMEOUT", "90"))
# nex-n2-pro is a REASONING model: it emits `reasoning_content` before the final
# `content`. A small budget gets consumed mid-reasoning (finish_reason=length)
# and `content` comes back empty, so give it generous headroom.
NEX_OCR_MAX_TOKENS: int = int(os.environ.get("NEX_OCR_MAX_TOKENS", "1500"))


def ocr_endpoint() -> str:
    """Full chat-completions URL for the OCR model."""
    base = NEX_OCR_BASE_URL
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def ocr_configured() -> bool:
    """True when the OCR gateway has a URL and key."""
    return bool(NEX_OCR_BASE_URL and NEX_OCR_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════
#  学科网 (XUEKE) question provider — tag-filtered question feed
# ═══════════════════════════════════════════════════════════════════════════
# A third question source besides AI-generation and the local bank: pull
# questions matching a tag from 学科网's API. The exact API contract differs per
# account, so the endpoint/key are configured here and the response is normalised
# in main.XuekeProvider (which documents the expected JSON shape). When unset the
# provider reports itself unavailable and the caller falls back to the bank.
XUEKE_BASE_URL: str = os.environ.get("XUEKE_BASE_URL", "").rstrip("/")
XUEKE_API_KEY: str = os.environ.get("XUEKE_API_KEY", "")
# Path appended to the base URL for a tag query (override if the API differs).
XUEKE_SEARCH_PATH: str = os.environ.get("XUEKE_SEARCH_PATH", "/questions/search")
XUEKE_TIMEOUT: float = float(os.environ.get("XUEKE_TIMEOUT", "10"))


def xueke_configured() -> bool:
    """True when the 学科网 provider has a URL and key."""
    return bool(XUEKE_BASE_URL and XUEKE_API_KEY)


def xueke_endpoint() -> str:
    """Full tag-search URL for the 学科网 provider."""
    return XUEKE_BASE_URL + XUEKE_SEARCH_PATH


def is_configured() -> bool:
    """True when we have enough to attempt a gateway call."""
    return bool(CLAUDE_BASE_URL and CLAUDE_API_KEY)


def valid_model(model_id: str) -> str:
    """Return model_id if it is one of the configured ids, else the default."""
    ids = {m["id"] for m in CLAUDE_MODELS}
    return model_id if model_id in ids else CLAUDE_DEFAULT_MODEL
