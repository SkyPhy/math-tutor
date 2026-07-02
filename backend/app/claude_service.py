"""
LLM gateway client — multi-provider (Anthropic + OpenAI-compatible).
=====================================================================
Historically this spoke only to an Anthropic-compatible gateway; it now routes
to whichever provider owns the selected model. Two wire protocols are supported:

  • "anthropic" — POST {base}/v1/messages           (Claude)
  • "openai"    — POST {base}/v1/chat/completions    (DeepSeek, GPT, …)

The public surface is unchanged: callers still do
`claude_service.complete(system, messages, model=…, …)` and catch `ClaudeError`,
so reasoner.py / sympy_compute.py / main.py need no changes. The model actually
used is chosen by providers.resolve_model() — the single choke point that clamps
every request to the ADMIN-configured pool (and honours a forced model), so a
student can never call a model outside the pool.

Still stdlib-only (urllib) and still resilient: per-PROVIDER circuit breakers
(one flaky provider doesn't disable the others), a per-session rate limit, and an
availability probe so callers can fall back to the template SocraticEngine.
"""

import json
import time
import urllib.request
import urllib.error
from collections import deque
from threading import Lock
from typing import Any, Dict, List, Optional

from . import config
from . import providers


class ClaudeError(Exception):
    """Raised when a gateway call cannot produce a usable completion. (Name kept
    for backwards-compatibility; it now covers every provider, not just Claude.)"""


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
        # One circuit breaker PER PROVIDER, created on demand — a DeepSeek outage
        # must not disable Claude and vice-versa.
        self._breakers: Dict[str, _CircuitBreaker] = {}
        self._breakers_lock = Lock()
        self._limiter = _RateLimiter(config.CLAUDE_RATE_PER_HOUR)

    def _breaker(self, provider: str) -> _CircuitBreaker:
        with self._breakers_lock:
            b = self._breakers.get(provider)
            if b is None:
                b = _CircuitBreaker(
                    config.CLAUDE_BREAKER_THRESHOLD, config.CLAUDE_BREAKER_COOLDOWN)
                self._breakers[provider] = b
            return b

    # ── Status ────────────────────────────────────────────────────────────
    def available(self) -> bool:
        """Ready to take a real call on SOME model right now? True when at least
        one usable+enabled model's provider breaker is closed."""
        for e in providers.enabled_pool():
            if self._breaker(e["provider"]).allow():
                return True
        return False

    def status(self) -> Dict[str, Any]:
        pool = providers.enabled_pool()
        provs = sorted({e["provider"] for e in pool})
        return {
            "configured": bool(pool),
            "providers": {
                p: {"circuit_open": self._breaker(p).is_open} for p in provs
            },
            "pool_size": len(pool),
            "default_model": providers.default_model(),
            "forced_model": providers.public_pool().get("forced_model"),
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
        timeout: Optional[float] = None,
    ) -> str:
        """Send a completion request to whichever provider owns the resolved model
        and return the concatenated text. `model` is the REQUESTED model; the model
        actually used is providers.resolve_model(model) (pool-clamped + forced).
        Raises ClaudeError on misconfiguration, rate-limit, open circuit, transport
        error, bad status, or empty/unexpected payload."""
        model_id = providers.resolve_model(model)
        entry = providers.get_model(model_id)
        # Unknown id (e.g. the Claude default when nothing is configured): fall back
        # to a synthetic Claude/anthropic entry from config, so behaviour matches the
        # original Claude-only client.
        if entry is None:
            entry = {
                "provider": "claude", "protocol": "anthropic",
                "base_url": config.CLAUDE_BASE_URL, "api_key": config.CLAUDE_API_KEY,
                "auth_header": config.CLAUDE_AUTH_HEADER,
                "anthropic_version": config.CLAUDE_ANTHROPIC_VERSION,
            }

        if not (entry.get("base_url") and entry.get("api_key")):
            raise ClaudeError(
                f"Model '{model_id}' ({entry.get('provider')}) is not configured "
                "(.env missing this provider's BASE_URL / API_KEY).")

        breaker = self._breaker(entry["provider"])
        if not breaker.allow():
            raise ClaudeError(
                f"{entry['provider']} temporarily disabled (circuit breaker open).")
        if not self._limiter.allow(session_id):
            raise ClaudeError("Per-session rate limit reached. Try again later.")

        try:
            if entry["protocol"] == "openai":
                text = self._call_openai(entry, model_id, system, messages,
                                         max_tokens, temperature, timeout)
            else:
                text = self._call_anthropic(entry, model_id, system, messages,
                                            max_tokens, temperature, timeout)
            breaker.record_success()
            return text
        except urllib.error.HTTPError as e:
            breaker.record_failure()
            detail = ""
            try:
                detail = e.read().decode("utf-8")[:500]
            except Exception:
                pass
            raise ClaudeError(f"Gateway HTTP {e.code}: {detail or e.reason}")
        except urllib.error.URLError as e:
            breaker.record_failure()
            raise ClaudeError(f"Gateway unreachable: {e.reason}")
        except ClaudeError:
            breaker.record_failure()
            raise
        except Exception as e:  # JSON / decoding / unexpected
            breaker.record_failure()
            raise ClaudeError(f"Unexpected gateway error: {e}")

    # ── protocol: Anthropic Messages ────────────────────────────────────────
    def _call_anthropic(self, entry, model_id, system, messages,
                        max_tokens, temperature, timeout) -> str:
        payload = {
            "model": model_id,
            "max_tokens": max_tokens or config.CLAUDE_MAX_TOKENS,
            "temperature": (
                config.CLAUDE_TEMPERATURE if temperature is None else temperature
            ),
            "system": system,
            "messages": messages,
        }
        headers = {
            "content-type": "application/json",
            "anthropic-version": entry.get("anthropic_version",
                                           config.CLAUDE_ANTHROPIC_VERSION),
        }
        if entry.get("auth_header") == "authorization":
            headers["authorization"] = f"Bearer {entry['api_key']}"
        else:
            headers["x-api-key"] = entry["api_key"]

        url = f"{entry['base_url']}/v1/messages"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout or config.CLAUDE_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
        return self._extract_anthropic_text(body)

    # ── protocol: OpenAI Chat Completions ───────────────────────────────────
    def _call_openai(self, entry, model_id, system, messages,
                     max_tokens, temperature, timeout) -> str:
        # OpenAI carries the system prompt as the first message (role "system"),
        # unlike Anthropic's top-level `system` field.
        chat_messages: List[Dict[str, str]] = []
        if system:
            chat_messages.append({"role": "system", "content": system})
        chat_messages.extend(messages or [])
        payload = {
            "model": model_id,
            "max_tokens": max_tokens or config.CLAUDE_MAX_TOKENS,
            "temperature": (
                config.CLAUDE_TEMPERATURE if temperature is None else temperature
            ),
            "messages": chat_messages,
        }
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {entry['api_key']}",
        }
        url = config.openai_chat_endpoint(entry["base_url"])
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout or config.CLAUDE_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
        return self._extract_openai_text(body)

    # ── response parsers ────────────────────────────────────────────────────
    @staticmethod
    def _extract_anthropic_text(body: str) -> str:
        """Pull the text out of an Anthropic Messages response."""
        try:
            obj = json.loads(body)
        except json.JSONDecodeError:
            raise ClaudeError("Gateway returned non-JSON response.")

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

    @staticmethod
    def _extract_openai_text(body: str) -> str:
        """Pull the assistant text out of an OpenAI Chat Completions response."""
        try:
            obj = json.loads(body)
        except json.JSONDecodeError:
            raise ClaudeError("Gateway returned non-JSON response.")

        if isinstance(obj, dict) and obj.get("error"):
            err = obj["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise ClaudeError(f"Gateway error: {msg or 'unknown error'}")

        choices = obj.get("choices") if isinstance(obj, dict) else None
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = msg.get("content", "")
            if isinstance(content, list):  # some gateways return content parts
                content = "".join(p.get("text", "") for p in content
                                  if isinstance(p, dict))
            content = (content or "").strip() if isinstance(content, str) else ""
            if content:
                return content
        raise ClaudeError("Gateway response contained no text content.")


# Singleton used across the app. (Name kept for backwards-compatibility; it now
# fronts every provider, not just Claude.)
claude_service = ClaudeService()
