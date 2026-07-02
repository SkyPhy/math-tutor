"""
model_policy.py — ADMIN-controlled runtime overlay for the LLM model pool.
==========================================================================
Which models a STUDENT may pick is decided by two layers:

  1. The .env CANDIDATE catalogue + per-provider config (config.py / providers.py)
     — what models could physically be used at all ("usable").
  2. THIS runtime overlay — an ADMIN-only switch, persisted in SQLite, that
     enables/disables individual models and can FORCE a single model on everyone
     ("强制分配"). It survives restarts and can be flipped without editing .env.

The student-selectable pool = usable ∧ enabled (see providers.enabled_pool()).

⚠️  ADMIN-ONLY — never student-controllable.
    The enable/disable + force switch is a privileged control. The FastAPI layer
    guards the write endpoints with `require_admin`, and the frontend must NEVER
    surface these toggles to a normal student (only to accounts whose role is
    "admin"). This is a hard product rule — see docs/MODELS_AND_PROVIDERS.md.
    Do not add a code path that lets a student flip availability or the forced
    model; that would defeat the whole point of the pool.

Storage is intentionally tiny (stdlib sqlite3, no ORM), mirroring auth.py:
  • table `model_enabled(model_id TEXT PK, enabled INT)` — per-model override.
    A model with NO row falls back to its catalogue `available_default` (True).
  • table `model_setting(key TEXT PK, value TEXT)` — singletons, currently just
    `forced_model` (empty string = not forced).
"""

from __future__ import annotations

import os
import sqlite3
from typing import Dict, Optional

from . import config

# Reuse the same data/ directory convention as auth.py / exam.py (one level up
# from this app/ package) so all SQLite files live together.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "model_policy.db")

_FORCED_KEY = "forced_model"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the overlay tables if absent, and seed the forced-model setting
    from LLM_FORCED_MODEL on FIRST run only (so a runtime change isn't clobbered
    by the .env default on every restart). Safe to call on every startup."""
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS model_enabled ("
            " model_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS model_setting ("
            " key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        # Seed forced_model from .env only if the row doesn't exist yet.
        row = conn.execute(
            "SELECT value FROM model_setting WHERE key = ?", (_FORCED_KEY,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO model_setting (key, value) VALUES (?, ?)",
                (_FORCED_KEY, config.LLM_FORCED_MODEL or ""),
            )
        conn.commit()


# ── per-model enable overrides ──────────────────────────────────────────────
def get_overrides() -> Dict[str, bool]:
    """Every explicit enable/disable override, {model_id: enabled}. Models with
    no row are absent here (caller falls back to the catalogue default)."""
    try:
        with _connect() as conn:
            rows = conn.execute("SELECT model_id, enabled FROM model_enabled").fetchall()
    except sqlite3.Error:
        return {}
    return {r["model_id"]: bool(r["enabled"]) for r in rows}


def set_enabled(model_id: str, enabled: bool) -> None:
    """Admin action: enable/disable one model for students (upsert)."""
    model_id = (model_id or "").strip()
    if not model_id:
        return
    with _connect() as conn:
        conn.execute(
            "INSERT INTO model_enabled (model_id, enabled) VALUES (?, ?) "
            "ON CONFLICT(model_id) DO UPDATE SET enabled = excluded.enabled",
            (model_id, 1 if enabled else 0),
        )
        conn.commit()


# ── forced model (admin 强制分配) ────────────────────────────────────────────
def get_forced() -> Optional[str]:
    """The model id every student is forced onto, or None when not forced."""
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT value FROM model_setting WHERE key = ?", (_FORCED_KEY,)
            ).fetchone()
    except sqlite3.Error:
        return None
    val = (row["value"] if row else "") or ""
    return val.strip() or None


def set_forced(model_id: Optional[str]) -> None:
    """Admin action: force everyone onto `model_id` (or clear with None/'')."""
    val = (model_id or "").strip()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO model_setting (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (_FORCED_KEY, val),
        )
        conn.commit()
