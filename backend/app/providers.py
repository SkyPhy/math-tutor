"""
providers.py — the multi-provider LLM model catalogue + pool resolution.
=========================================================================
One place that answers "which models exist, which may a student pick, and which
model does a given request actually run on".

Two independent inputs are merged here:
  • CANDIDATE catalogue — assembled from config.py's per-provider settings
    (Claude = Anthropic protocol; DeepSeek + GPT = OpenAI-compatible protocol).
    A model is "usable" only if its provider has a BASE_URL and API_KEY.
  • ADMIN overlay — model_policy.py's runtime enable/disable + forced-model.

  student-selectable pool  =  usable  ∧  admin-enabled          (enabled_pool)
  the model a call runs on =  resolve_model(requested)

`resolve_model` is the single choke point every LLM call passes through
(claude_service.complete calls it), so a student can NEVER escape the pool:
  1. If the admin forced a model (and it is usable) → that model, always.
  2. Else the requested model, but only if it is in the pool.
  3. Else the pool's default.

⚠️  The enable/disable + force controls are ADMIN-ONLY (model_policy.py). This
    module only READS the overlay; it never lets a student mutate it.

No dependency on claude_service (would be circular) — this is pure data + policy.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import config
from . import model_policy


# Human-facing provider names for the UI ("Opus 4.8 · Claude").
PROVIDER_LABELS = {"claude": "Claude", "deepseek": "DeepSeek", "openai": "GPT"}


def _catalogue() -> List[Dict[str, Any]]:
    """Assemble the full CANDIDATE catalogue from config, deduped by model id
    (first occurrence wins). Each entry carries everything the transport needs."""
    entries: List[Dict[str, Any]] = []

    # Claude — Anthropic protocol (the original gateway).
    for m in config.CLAUDE_MODELS:
        entries.append({
            "id": m["id"], "label": m["label"],
            "provider": "claude", "protocol": "anthropic",
            "base_url": config.CLAUDE_BASE_URL, "api_key": config.CLAUDE_API_KEY,
            "auth_header": config.CLAUDE_AUTH_HEADER,
            "anthropic_version": config.CLAUDE_ANTHROPIC_VERSION,
            "available_default": True,
        })
    # DeepSeek — OpenAI-compatible protocol.
    for m in config.DEEPSEEK_MODELS:
        entries.append({
            "id": m["id"], "label": m["label"],
            "provider": "deepseek", "protocol": "openai",
            "base_url": config.DEEPSEEK_BASE_URL, "api_key": config.DEEPSEEK_API_KEY,
            "auth_header": "authorization",
            "available_default": True,
        })
    # OpenAI / GPT — OpenAI-compatible protocol.
    for m in config.OPENAI_MODELS:
        entries.append({
            "id": m["id"], "label": m["label"],
            "provider": "openai", "protocol": "openai",
            "base_url": config.OPENAI_BASE_URL, "api_key": config.OPENAI_API_KEY,
            "auth_header": "authorization",
            "available_default": True,
        })

    seen: set = set()
    deduped: List[Dict[str, Any]] = []
    for e in entries:
        if e["id"] and e["id"] not in seen:
            seen.add(e["id"])
            deduped.append(e)
    return deduped


def list_catalogue() -> List[Dict[str, Any]]:
    """The full CANDIDATE catalogue (usable or not, enabled or not)."""
    return _catalogue()


def get_model(model_id: str) -> Optional[Dict[str, Any]]:
    """The catalogue entry for `model_id`, or None if unknown."""
    if not model_id:
        return None
    for e in _catalogue():
        if e["id"] == model_id:
            return e
    return None


def usable(model_id: str) -> bool:
    """True when `model_id`'s provider is actually configured (base_url + key)."""
    e = get_model(model_id)
    return bool(e and e.get("base_url") and e.get("api_key"))


def _is_enabled(entry: Dict[str, Any], overrides: Dict[str, bool]) -> bool:
    """Admin enable state: explicit override if present, else catalogue default."""
    return overrides.get(entry["id"], entry.get("available_default", True))


def enabled_pool() -> List[Dict[str, Any]]:
    """The student-selectable pool: usable AND admin-enabled, in catalogue order."""
    overrides = model_policy.get_overrides()
    return [e for e in _catalogue()
            if e.get("base_url") and e.get("api_key") and _is_enabled(e, overrides)]


def pool_ids() -> set:
    return {e["id"] for e in enabled_pool()}


def default_model() -> str:
    """The model a call falls back to. Forced model wins (if usable); else the
    Claude default when it is in the pool; else the first pooled model; else the
    Claude default id as a stable string (even if currently unusable)."""
    forced = model_policy.get_forced()
    if forced and usable(forced):
        return forced
    pool = enabled_pool()
    ids = {e["id"] for e in pool}
    if config.CLAUDE_DEFAULT_MODEL in ids:
        return config.CLAUDE_DEFAULT_MODEL
    if pool:
        return pool[0]["id"]
    return config.CLAUDE_DEFAULT_MODEL


def resolve_model(requested: Optional[str]) -> str:
    """The SINGLE choke point: map a requested model id to the one that actually
    runs, clamped to the admin pool and overridden by a forced model. See module
    docstring for the ordering."""
    forced = model_policy.get_forced()
    if forced and usable(forced):
        return forced
    if requested and requested in pool_ids():
        return requested
    return default_model()


def public_pool() -> Dict[str, Any]:
    """Payload for the student-facing model picker (GET /models): only the pool
    they may choose from, the default, and whether a forced model locks the UI."""
    forced = model_policy.get_forced()
    forced_active = bool(forced and usable(forced))
    models = [
        {"id": e["id"], "label": e["label"],
         "provider": e["provider"],
         "provider_label": PROVIDER_LABELS.get(e["provider"], e["provider"])}
        for e in enabled_pool()
    ]
    return {
        "models": models,
        "default": default_model(),
        "forced_model": forced if forced_active else None,
    }


def admin_catalogue() -> Dict[str, Any]:
    """Payload for the ADMIN panel (GET /admin/models): the FULL catalogue with
    per-model usable/enabled state, plus the forced model. Admin-only."""
    overrides = model_policy.get_overrides()
    forced = model_policy.get_forced()
    models = [
        {"id": e["id"], "label": e["label"],
         "provider": e["provider"],
         "provider_label": PROVIDER_LABELS.get(e["provider"], e["provider"]),
         "usable": bool(e.get("base_url") and e.get("api_key")),
         "enabled": _is_enabled(e, overrides)}
        for e in _catalogue()
    ]
    return {"models": models, "forced_model": forced or None}
