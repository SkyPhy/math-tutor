"""
Personal workspace — student draft / answer library (SQLite)
============================================================
Backs the 校对屏 (③ check screen) "存草稿 / 提交" affordances (v0.4.2a). A student's
recognised-and-corrected writing can be named and stashed per question, so they can
stop and resume later ("断点续作"). This is the 草图's "个人 tmp 数据库（带问题编号）".

Two states per draft:
  • ``tmp``   — a work-in-progress draft saved with 「存草稿」.
  • ``final`` — the version the student 「提交」ed (which then drives /verify or the
    AI assistant, depending on the flow). Kept here too so the submitted text is
    recoverable.

`owner` scopes a draft to one person: the logged-in username when signed in, else
the anonymous `session_id`. Standard library only (sqlite3), mirroring exam.py /
auth.py so there is no extra dependency and the file lives in the shared data/ dir.
"""

from __future__ import annotations

import os
import sqlite3
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Persistent data lives in the shared backend/data/ directory (see auth.py / exam.py),
# one level up from this app/ package.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "workspace.db")

VALID_STATUS = ("tmp", "final")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS work_drafts (
                id          TEXT PRIMARY KEY,
                owner       TEXT NOT NULL,
                question_id TEXT,
                filename    TEXT,
                content_md  TEXT,
                render_mode TEXT,
                status      TEXT NOT NULL DEFAULT 'tmp',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """
        )
        # "Every draft this student has for this question" is the common lookup
        # (校对屏 lists them so a saved draft can be reopened and continued).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_work_owner_q ON work_drafts(owner, question_id)"
        )
        conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return "w-" + secrets.token_hex(6)


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "owner": row["owner"],
        "question_id": row["question_id"],
        "filename": row["filename"],
        "content_md": row["content_md"],
        "render_mode": row["render_mode"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_draft(
    owner: str,
    *,
    question_id: Optional[str] = None,
    filename: Optional[str] = None,
    content_md: str = "",
    render_mode: Optional[str] = None,
    status: str = "tmp",
    draft_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update one draft, returning the stored row.

    When ``draft_id`` names an EXISTING draft owned by ``owner`` the row is updated
    in place (the "存草稿 → 续作 → 再存" loop reuses one row instead of piling up
    duplicates); otherwise a fresh draft is inserted. ``status`` is clamped to
    'tmp' | 'final'.
    """
    status = status if status in VALID_STATUS else "tmp"
    now = _now()
    with _connect() as conn:
        existing = None
        if draft_id:
            existing = conn.execute(
                "SELECT * FROM work_drafts WHERE id = ? AND owner = ?", (draft_id, owner)
            ).fetchone()
        if existing:
            conn.execute(
                "UPDATE work_drafts SET question_id = ?, filename = ?, content_md = ?, "
                "render_mode = ?, status = ?, updated_at = ? WHERE id = ?",
                (question_id, filename, content_md, render_mode, status, now, draft_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM work_drafts WHERE id = ?", (draft_id,)).fetchone()
            return _row_to_dict(row)
        new_id = _new_id()
        conn.execute(
            "INSERT INTO work_drafts (id, owner, question_id, filename, content_md, "
            "render_mode, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id, owner, question_id, filename, content_md, render_mode, status, now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM work_drafts WHERE id = ?", (new_id,)).fetchone()
        return _row_to_dict(row)


def list_drafts(owner: str, question_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """A student's drafts, newest first; optionally scoped to one question."""
    with _connect() as conn:
        if question_id:
            rows = conn.execute(
                "SELECT * FROM work_drafts WHERE owner = ? AND question_id = ? "
                "ORDER BY updated_at DESC LIMIT ?",
                (owner, question_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM work_drafts WHERE owner = ? ORDER BY updated_at DESC LIMIT ?",
                (owner, limit),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_draft(draft_id: str, owner: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """One draft by id (optionally asserting ownership), or None."""
    with _connect() as conn:
        if owner is not None:
            row = conn.execute(
                "SELECT * FROM work_drafts WHERE id = ? AND owner = ?", (draft_id, owner)
            ).fetchone()
        else:
            row = conn.execute("SELECT * FROM work_drafts WHERE id = ?", (draft_id,)).fetchone()
        return _row_to_dict(row) if row else None


def delete_draft(draft_id: str, owner: str) -> bool:
    """Remove a draft the student owns. Returns True if a row was deleted."""
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM work_drafts WHERE id = ? AND owner = ?", (draft_id, owner)
        )
        conn.commit()
        return cur.rowcount > 0


def count(owner: Optional[str] = None) -> int:
    with _connect() as conn:
        if owner is not None:
            return conn.execute(
                "SELECT COUNT(*) AS n FROM work_drafts WHERE owner = ?", (owner,)
            ).fetchone()["n"]
        return conn.execute("SELECT COUNT(*) AS n FROM work_drafts").fetchone()["n"]
