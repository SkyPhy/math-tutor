"""
Experience memory — durable, cross-session learning (SQLite storage).
=====================================================================
Implements the blueprint's "Recursive Intelligence / Experience-Based Memory"
pillar with a PERSISTENT backing store, replacing the previous in-process
dictionary (which was lost on every restart).

What it remembers, per session:
  • the running conversation (role / content / hint level / timestamp),
  • every interaction (which expression, how many hints, did the user solve it),
  • derived signals — hint levels reached per expression, struggle patterns,
    successful strategies, total interactions, Socratic-compliance score.

From those it computes an ADAPTIVE CONTEXT (success rate, "needs more guidance",
"is advanced") that the Blending Instructions feed into the tutor's prompts so
guidance adapts to the learner over time — and now survives restarts.

Standard library only (sqlite3), mirroring auth.py / exam.py:
  • one short-lived connection per call (thread-safe under FastAPI's threadpool),
  • all queries parameterised (no SQL injection),
  • data lives in the shared backend/data/ directory, one level up from app/.

The public class keeps the EXACT method surface the old in-memory
`ExperienceMemory` had, so main.py's call sites are unchanged:
    get_or_create_session, record_interaction, add_message,
    get_conversation, get_adaptive_context.
`add_message` accepts any object exposing .role / .content / .hint_level
(duck-typed) so this module needn't import main.py's pydantic models.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

# Persistent data lives in backend/data/ (one level up from this app/ package),
# the same directory auth.py and exam.py use.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "memory.db")


# ── Connection / schema ────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the tables if they don't exist. Safe to call on every startup."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mem_sessions (
                id                  TEXT PRIMARY KEY,
                created_at          TEXT NOT NULL,
                socratic_compliance REAL DEFAULT 1.0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mem_messages (
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                hint_level INTEGER,
                timestamp  TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES mem_sessions(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mem_interactions (
                session_id  TEXT NOT NULL,
                expression  TEXT NOT NULL,
                hint_level  INTEGER NOT NULL,
                user_solved INTEGER NOT NULL DEFAULT 0,
                timestamp   TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES mem_sessions(id) ON DELETE CASCADE
            )
            """
        )
        # Per-session lookups are the hot path → index on session_id.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_msg_sess ON mem_messages(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_int_sess ON mem_interactions(session_id)")
        conn.commit()


def _now() -> str:
    return datetime.now().isoformat()


class PersistentExperienceMemory:
    """Durable experience memory. Same surface as the old in-memory version,
    but every read/write goes through SQLite so state survives restarts and is
    shared across sessions/processes."""

    # ── session lifecycle ──────────────────────────────────────────────────
    def _ensure_session(self, conn: sqlite3.Connection, session_id: str) -> None:
        exists = conn.execute(
            "SELECT 1 FROM mem_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO mem_sessions (id, created_at, socratic_compliance) VALUES (?, ?, ?)",
                (session_id, _now(), 1.0),
            )

    def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Reconstruct the full session dict (same shape the old dict had) from
        SQLite, creating the session row on first reference."""
        with _connect() as conn:
            self._ensure_session(conn, session_id)
            conn.commit()
            return self._assemble_session(conn, session_id)

    def _assemble_session(self, conn: sqlite3.Connection, session_id: str) -> Dict[str, Any]:
        srow = conn.execute(
            "SELECT created_at, socratic_compliance FROM mem_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        created_at = srow["created_at"] if srow else _now()
        compliance = srow["socratic_compliance"] if srow else 1.0

        conversation = [
            {
                "role": r["role"],
                "content": r["content"],
                "hint_level": r["hint_level"],
                "timestamp": r["timestamp"],
            }
            for r in conn.execute(
                "SELECT role, content, hint_level, timestamp FROM mem_messages "
                "WHERE session_id = ? ORDER BY rowid",
                (session_id,),
            ).fetchall()
        ]

        interactions = conn.execute(
            "SELECT expression, hint_level, user_solved, timestamp FROM mem_interactions "
            "WHERE session_id = ? ORDER BY rowid",
            (session_id,),
        ).fetchall()

        hint_levels_used: Dict[str, int] = {}
        struggle_patterns: List[Dict[str, Any]] = []
        successful_strategies: List[Dict[str, Any]] = []
        expressions_solved: List[str] = []
        for r in interactions:
            expr = r["expression"]
            lvl = r["hint_level"]
            hint_levels_used[expr] = max(hint_levels_used.get(expr, 0), lvl)
            if r["user_solved"]:
                successful_strategies.append(
                    {"expression": expr, "hints_needed": lvl, "timestamp": r["timestamp"]}
                )
                if expr not in expressions_solved:
                    expressions_solved.append(expr)
            elif lvl >= 3:
                struggle_patterns.append({"expression": expr, "timestamp": r["timestamp"]})

        return {
            "id": session_id,
            "created_at": created_at,
            "conversation": conversation,
            "expressions_solved": expressions_solved,
            "hint_levels_used": hint_levels_used,
            "struggle_patterns": struggle_patterns,
            "successful_strategies": successful_strategies,
            "total_interactions": len(interactions),
            "socratic_compliance": compliance,
        }

    # ── writes ─────────────────────────────────────────────────────────────
    def record_interaction(self, session_id: str, expression: str,
                           hint_level: int, user_solved: bool) -> None:
        with _connect() as conn:
            self._ensure_session(conn, session_id)
            conn.execute(
                "INSERT INTO mem_interactions (session_id, expression, hint_level, user_solved, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, expression, int(hint_level), 1 if user_solved else 0, _now()),
            )
            conn.commit()

    def add_message(self, session_id: str, message: Any) -> None:
        """Persist a conversation message. `message` is duck-typed: any object
        with .role / .content and an optional .hint_level."""
        with _connect() as conn:
            self._ensure_session(conn, session_id)
            conn.execute(
                "INSERT INTO mem_messages (session_id, role, content, hint_level, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    getattr(message, "role", "system"),
                    getattr(message, "content", ""),
                    getattr(message, "hint_level", None),
                    _now(),
                ),
            )
            conn.commit()

    # ── reads ──────────────────────────────────────────────────────────────
    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        with _connect() as conn:
            return [
                {
                    "role": r["role"],
                    "content": r["content"],
                    "hint_level": r["hint_level"],
                    "timestamp": r["timestamp"],
                }
                for r in conn.execute(
                    "SELECT role, content, hint_level, timestamp FROM mem_messages "
                    "WHERE session_id = ? ORDER BY rowid",
                    (session_id,),
                ).fetchall()
            ]

    def get_adaptive_context(self, session_id: str) -> Dict[str, Any]:
        """Blending-instruction context derived from the persisted history.
        Same formula as the original in-memory implementation."""
        with _connect() as conn:
            self._ensure_session(conn, session_id)
            conn.commit()
            total = conn.execute(
                "SELECT COUNT(*) AS n FROM mem_interactions WHERE session_id = ?",
                (session_id,),
            ).fetchone()["n"]
            successes = conn.execute(
                "SELECT COUNT(*) AS n FROM mem_interactions WHERE session_id = ? AND user_solved = 1",
                (session_id,),
            ).fetchone()["n"]
            struggles = conn.execute(
                "SELECT COUNT(*) AS n FROM mem_interactions "
                "WHERE session_id = ? AND user_solved = 0 AND hint_level >= 3",
                (session_id,),
            ).fetchone()["n"]

        success_rate = successes / max(total, 1)
        return {
            "interaction_count": total,
            "struggle_count": struggles,
            "success_rate": success_rate,
            "needs_more_guidance": struggles > 2,
            "is_advanced": (successes > 5 and total > 0 and success_rate > 0.8),
        }


# Module-level singleton, mirroring the old `memory = ExperienceMemory()`.
memory = PersistentExperienceMemory()
