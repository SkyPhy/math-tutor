"""
Logic-flaw diagnosis — per-student & AI-self profiles over the tag vocabulary.
=============================================================================
The v2.0 core differentiator (goals 5/6): find which LOGIC-THINKING TYPES a
student — and the AI itself — is weak at, so training targets the flaw rather
than drilling knowledge points.

Two signals, both keyed by the dynamic tags (tags.py):
  • STUDENT outcomes — per session, per tag: attempts vs successes, fed from
    /verify grading. Low success on a logic type ⇒ a student logic flaw.
  • AI-SELF signals — global, per tag: how often the tutor's OWN multi-path
    consensus DIVERGES on questions of that type (low agreement ⇒ the tutor's
    own reasoning is shaky there). Consensus divergence is the self-diagnosis seed.

Own database (data/diagnosis.db). Standard library only (sqlite3).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "diagnosis.db")

# A logic type counts as a student flaw below this success rate (with ≥1 attempt).
WEAK_SUCCESS_THRESHOLD = 0.6
# Consensus "diverged" when fewer than ~2/3 of the independent paths agreed.
LOW_AGREEMENT_THRESHOLD = 0.67


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tag_outcomes (
                session_id TEXT NOT NULL,
                tag        TEXT NOT NULL,
                kind       TEXT NOT NULL,
                attempts   INTEGER DEFAULT 0,
                successes  INTEGER DEFAULT 0,
                last_at    TEXT,
                PRIMARY KEY (session_id, tag)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS self_signals (
                tag           TEXT PRIMARY KEY,
                kind          TEXT NOT NULL,
                graded        INTEGER DEFAULT 0,
                agreement_sum REAL DEFAULT 0,
                low_agreement INTEGER DEFAULT 0,
                last_at       TEXT
            )
            """
        )
        conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── STUDENT outcomes (per session, per tag) ─────────────────────────────────
def record_student_outcome(session_id: str, tag: str, kind: str, correct: bool) -> None:
    """One graded attempt on a tag: bump attempts, and successes if correct."""
    if not session_id or not tag:
        return
    with _connect() as conn:
        conn.execute(
            """INSERT INTO tag_outcomes (session_id, tag, kind, attempts, successes, last_at)
               VALUES (?, ?, ?, 1, ?, ?)
               ON CONFLICT(session_id, tag) DO UPDATE SET
                   attempts  = attempts + 1,
                   successes = successes + ?,
                   last_at   = ?""",
            (session_id, tag, kind, 1 if correct else 0, _now(),
             1 if correct else 0, _now()),
        )
        conn.commit()


def _rate(successes: int, attempts: int) -> Optional[float]:
    return round(successes / attempts, 3) if attempts else None


def student_profile(session_id: str) -> Dict[str, Any]:
    """Per-tag stats for a session + the ranked weak LOGIC types (the flaws)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tag_outcomes WHERE session_id = ? ORDER BY tag", (session_id,)
        ).fetchall()
    tags_stats = [{
        "tag": r["tag"], "kind": r["kind"], "attempts": r["attempts"],
        "successes": r["successes"], "success_rate": _rate(r["successes"], r["attempts"]),
    } for r in rows]

    logic = [t for t in tags_stats if t["kind"] == "logic" and t["attempts"] > 0]
    weak = sorted(
        (t for t in logic if (t["success_rate"] or 0) < WEAK_SUCCESS_THRESHOLD),
        key=lambda t: ((t["success_rate"] or 0), -t["attempts"]),
    )
    return {
        "session_id": session_id,
        "tags": tags_stats,
        "weak_logic": [
            {"tag": t["tag"], "success_rate": t["success_rate"], "attempts": t["attempts"]}
            for t in weak
        ],
    }


def weak_logic_tags(session_id: str, limit: int = 1) -> List[str]:
    """Weakest logic-type tag names for adaptive targeting ([] if no signal yet)."""
    return [w["tag"] for w in student_profile(session_id)["weak_logic"][:limit]]


# ── AI-SELF signals (global, per tag) ───────────────────────────────────────
def record_self_signal(tag: str, kind: str, agreement: Optional[float]) -> None:
    """One self-graded question of this tag: track how much the tutor's own
    multi-path consensus agreed (low agreement ⇒ shaky self-reasoning here)."""
    if not tag or agreement is None:
        return
    low = 1 if agreement < LOW_AGREEMENT_THRESHOLD else 0
    with _connect() as conn:
        conn.execute(
            """INSERT INTO self_signals (tag, kind, graded, agreement_sum, low_agreement, last_at)
               VALUES (?, ?, 1, ?, ?, ?)
               ON CONFLICT(tag) DO UPDATE SET
                   graded        = graded + 1,
                   agreement_sum = agreement_sum + ?,
                   low_agreement = low_agreement + ?,
                   last_at       = ?""",
            (tag, kind, agreement, low, _now(), agreement, low, _now()),
        )
        conn.commit()


def self_profile(limit: Optional[int] = None) -> Dict[str, Any]:
    """Per-tag self-consensus health, ranked by DIVERGENCE (1 − avg agreement)."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM self_signals WHERE graded > 0").fetchall()
    items = []
    for r in rows:
        avg = round(r["agreement_sum"] / r["graded"], 3) if r["graded"] else None
        items.append({
            "tag": r["tag"], "kind": r["kind"], "graded": r["graded"],
            "avg_agreement": avg, "low_agreement": r["low_agreement"],
            "divergence": round(1 - avg, 3) if avg is not None else None,
        })
    items.sort(key=lambda t: (-(t["divergence"] or 0), -t["graded"]))
    if limit:
        items = items[:limit]
    return {"tags": items}


def counts() -> Dict[str, int]:
    with _connect() as conn:
        a = conn.execute("SELECT COUNT(*) AS n FROM tag_outcomes").fetchone()["n"]
        b = conn.execute("SELECT COUNT(*) AS n FROM self_signals").fetchone()["n"]
    return {"student_rows": a, "self_rows": b}
