"""
ClaudeService — Anthropic-compatible gateway client.
=====================================================
Talks to `{CLAUDE_BASE_URL}/v1/messages` using only the standard library
(urllib), so no extra pip install is required. Built for resilience so the
tutor degrades gracefully instead of crashing:

  • timeout per call (config.CLAUDE_TIMEOUT)
  • circuit breaker: after N consecutive failures, stop calling for a cooldown
  • per-session rate limit (calls/hour)
  • availability probe so callers can fall back to the template engine

`complete()` raises ClaudeError on any failure; the FastAPI layer catches it
and falls back to SocraticEngine, keeping SymPy as the verification anchor.
"""

import json
import time
import urllib.request
import urllib.error
from collections import deque
from threading import Lock
from typing import List, Dict, Optional

import config


class ClaudeError(Exception):
    """Raised when a gateway call cannot produce a usable completion."""


class _CircuitBreaker:
    """Trips open after `threshold` consecutive failures, then half-opens
    again after `cooldown` seconds so the service can recover on its own."""

    def __init__(self, threshold: int, cooldown: float):
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._opened_at: Optional[float] = None
        self._lock = Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if (time.time() - self._opened_at) >= self.cooldown:
                # Cooldown elapsed → half-open: allow a trial call.
                self._opened_at = None
                self._failures = 0
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.threshold and self._opened_at is None:
                self._opened_at = time.time()

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._opened_at is not None and (
                time.time() - self._opened_at
            ) < self.cooldown


class _RateLimiter:
    """Sliding-window per-session limiter: at most `per_hour` calls / 3600s."""

    def __init__(self, per_hour: int):
        self.per_hour = per_hour
        self._hits: Dict[str, deque] = {}
        self._lock = Lock()

    def allow(self, session_id: str) -> bool:
        if self.per_hour <= 0:
            return True
        now = time.time()
        with self._lock:
            dq = self._hits.setdefault(session_id, deque())
            while dq and (now - dq[0]) > 3600:
                dq.popleft()
            if len(dq) >= self.per_hour:
                return False
            dq.append(now)
            return True


class ClaudeService:
    def __init__(self):
        self._breaker = _CircuitBreaker(
            config.CLAUDE_BREAKER_THRESHOLD, config.CLAUDE_BREAKER_COOLDOWN
        )
        self._limiter = _RateLimiter(config.CLAUDE_RATE_PER_HOUR)

    # ── Status ────────────────────────────────────────────────────────────
    def available(self) -> bool:
        """Ready to take a real call right now?"""
        return config.is_configured() and self._breaker.allow()

    def status(self) -> Dict:
        return {
            "configured": config.is_configured(),
            "circuit_open": self._breaker.is_open,
            "base_url_set": bool(config.CLAUDE_BASE_URL),
            "models": config.CLAUDE_MODELS,
            "default_model": config.CLAUDE_DEFAULT_MODEL,
        }

    # ── Core call ─────────────────────────────────────────────────────────
    def complete(
        self,
        system: str,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        session_id: str = "anon",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Send a Messages-API request and return the concatenated text.

        Raises ClaudeError on misconfiguration, rate-limit, open circuit,
        transport error, bad status, or empty/unexpected payload.
        """
        if not config.is_configured():
            raise ClaudeError("Claude gateway is not configured (.env missing "
                              "CLAUDE_BASE_URL / CLAUDE_API_KEY).")
        if not self._breaker.allow():
            raise ClaudeError("Claude temporarily disabled (circuit breaker open).")
        if not self._limiter.allow(session_id):
            raise ClaudeError("Per-session rate limit reached. Try again later.")

        model_id = config.valid_model(model or config.CLAUDE_DEFAULT_MODEL)
        payload = {
            "model": model_id,
            "max_tokens": max_tokens or config.CLAUDE_MAX_TOKENS,
            "temperature": (
                config.CLAUDE_TEMPERATURE if temperature is None else temperature
            ),
            "system": system,
            "messages": messages,
        }
        url = f"{config.CLAUDE_BASE_URL}/v1/messages"
        headers = {
            "content-type": "application/json",
            "anthropic-version": config.CLAUDE_ANTHROPIC_VERSION,
        }
        if config.CLAUDE_AUTH_HEADER == "authorization":
            headers["authorization"] = f"Bearer {config.CLAUDE_API_KEY}"
        else:
            headers["x-api-key"] = config.CLAUDE_API_KEY

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=config.CLAUDE_TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
            text = self._extract_text(body)
            self._breaker.record_success()
            return text
        except urllib.error.HTTPError as e:
            self._breaker.record_failure()
            detail = ""
            try:
                detail = e.read().decode("utf-8")[:500]
            except Exception:
                pass
            raise ClaudeError(f"Gateway HTTP {e.code}: {detail or e.reason}")
        except urllib.error.URLError as e:
            self._breaker.record_failure()
            raise ClaudeError(f"Gateway unreachable: {e.reason}")
        except ClaudeError:
            raise
        except Exception as e:  # JSON / decoding / unexpected
            self._breaker.record_failure()
            raise ClaudeError(f"Unexpected gateway error: {e}")

    @staticmethod
    def _extract_text(body: str) -> str:
        """Pull the text out of an Anthropic Messages response."""
        try:
            obj = json.loads(body)
        except json.JSONDecodeError:
            raise ClaudeError("Gateway returned non-JSON response.")

        # Anthropic error envelope.
        if isinstance(obj, dict) and obj.get("type") == "error":
            msg = (obj.get("error") or {}).get("message", "unknown error")
            raise ClaudeError(f"Gateway error: {msg}")

        content = obj.get("content") if isinstance(obj, dict) else None
        if isinstance(content, list):
            parts = [
                blk.get("text", "")
                for blk in content
                if isinstance(blk, dict) and blk.get("type") == "text"
            ]
            text = "".join(parts).strip()
            if text:
                return text
        raise ClaudeError("Gateway response contained no text content.")


# Singleton used across the app.
claude_service = ClaudeService()
