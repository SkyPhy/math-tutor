"""
Dynamic tag store — the evolving tag vocabulary, in its OWN database.
=====================================================================
Tags here are **data, not code**. Unlike exam.py's hard-coded `CATALOGUE`
(the 25 knowledge points from lesson/README.md) and `LOGIC_CATALOGUE` (the 13
logic-thinking types), the vocabulary in this store can grow and shrink at
runtime:

  • the AI may ADD a new tag it finds fitting (source='ai'),
  • ANY tag may be REMOVED — including the seeded lesson/README knowledge points
    (soft-delete via `active=0`, or hard delete).

exam.py's catalogues are only the initial SEED; once seeded, THIS store is the
source of truth for what tags exist. Lives in its own `data/tags.db` so the tag
vocabulary evolves independently of the question bank (`exams.db`).

Standard library only (sqlite3) — no extra dependency.
"""

from __future__ import annotations

import os
import json
import sqlite3
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Own database, alongside the other SQLite stores in backend/data/.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "tags.db")

# Tag kinds. New kinds may appear over time — this is not a closed set.
KIND_KNOWLEDGE = "knowledge"   # 知识点（lesson/README.md，可删）
KIND_LOGIC = "logic"           # 逻辑思维（解决问题）类型


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL UNIQUE,
                kind        TEXT NOT NULL,
                parent      TEXT,                 -- family / subdimension grouping (optional)
                description TEXT,                 -- human description
                meta        TEXT,                 -- JSON for kind-specific fields (logic move/flaw, …)
                source      TEXT DEFAULT 'ai',    -- 'seed' | 'ai' | 'user'
                active      INTEGER DEFAULT 1,     -- soft delete
                usage_count INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_kind_active ON tags(kind, active)")
        conn.commit()


def _new_id() -> str:
    return "tag-" + secrets.token_hex(5)


def _row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    meta = {}
    if r["meta"]:
        try:
            meta = json.loads(r["meta"])
        except (ValueError, TypeError):
            meta = {}
    return {
        "id": r["id"],
        "name": r["name"],
        "kind": r["kind"],
        "parent": r["parent"],
        "description": r["description"],
        "meta": meta,
        "source": r["source"],
        "active": bool(r["active"]),
        "usage_count": r["usage_count"],
        "created_at": r["created_at"],
    }


def get_tag(name: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tags WHERE name = ?", (name,)).fetchone()
        return _row_to_dict(row) if row else None


def add_tag(name: str, kind: str, parent: Optional[str] = None,
            description: Optional[str] = None, meta: Optional[Dict[str, Any]] = None,
            source: str = "ai") -> Dict[str, Any]:
    """Idempotent upsert by name. A brand-new name is inserted; an existing name
    is returned (re-activated if it had been soft-deleted, and back-filling any
    missing parent/description/meta). This is the entry point the AI uses to
    grow the vocabulary with a tag it judged fitting."""
    name = (name or "").strip()
    if not name:
        raise ValueError("tag name is required")
    existing = get_tag(name)
    now = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(meta, ensure_ascii=False) if meta else None

    with _connect() as conn:
        if existing:
            conn.execute(
                """UPDATE tags SET active = 1,
                       parent      = COALESCE(parent, ?),
                       description = COALESCE(description, ?),
                       meta        = COALESCE(meta, ?)
                   WHERE name = ?""",
                (parent, description, meta_json, name),
            )
            conn.commit()
            return get_tag(name)  # type: ignore[return-value]
        conn.execute(
            "INSERT INTO tags (id, name, kind, parent, description, meta, source, active, usage_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?)",
            (_new_id(), name, kind, parent, description, meta_json, source, now),
        )
        conn.commit()
    return get_tag(name)  # type: ignore[return-value]


def list_tags(kind: Optional[str] = None, include_inactive: bool = False) -> List[Dict[str, Any]]:
    q = "SELECT * FROM tags"
    clauses, params = [], []
    if kind:
        clauses.append("kind = ?"); params.append(kind)
    if not include_inactive:
        clauses.append("active = 1")
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY kind, parent, name"
    with _connect() as conn:
        return [_row_to_dict(r) for r in conn.execute(q, params).fetchall()]


def deactivate_tag(name: str) -> bool:
    """Soft-delete: mark inactive but keep the row (history / re-activation).
    Works on the seeded lesson/README tags too — nothing is protected."""
    with _connect() as conn:
        cur = conn.execute("UPDATE tags SET active = 0 WHERE name = ? AND active = 1", (name,))
        conn.commit()
        return cur.rowcount > 0


def remove_tag(name: str, hard: bool = False) -> bool:
    """Remove a tag. `hard=True` deletes the row outright; otherwise soft-delete."""
    if not hard:
        return deactivate_tag(name)
    with _connect() as conn:
        cur = conn.execute("DELETE FROM tags WHERE name = ?", (name,))
        conn.commit()
        return cur.rowcount > 0


def bump_usage(name: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE tags SET usage_count = usage_count + 1 WHERE name = ?", (name,))
        conn.commit()


def count(include_inactive: bool = False) -> int:
    q = "SELECT COUNT(*) AS n FROM tags" + ("" if include_inactive else " WHERE active = 1")
    with _connect() as conn:
        return conn.execute(q).fetchone()["n"]


def catalogue(include_inactive: bool = False) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Grouped view: kind → parent → [tags]. The dynamic replacement for
    exam.CATALOGUE / exam.LOGIC_CATALOGUE as the thing the UI/AI reads."""
    out: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for t in list_tags(include_inactive=include_inactive):
        out.setdefault(t["kind"], {}).setdefault(t["parent"] or "", []).append(t)
    return out


def seed_from_catalogues() -> int:
    """One-time seed from exam.py's hard-coded catalogues, so a fresh DB starts
    with today's vocabulary. No-op once any tag exists (so user/AI edits — adds
    AND deletes — are never clobbered on restart). Returns the number seeded."""
    if count(include_inactive=True) > 0:
        return 0
    # Imported here (not at module top) to keep import order simple; exam.py does
    # not import tags.py, so there is no circular dependency.
    from . import exam

    n = 0
    for dim, subs in exam.CATALOGUE.items():
        for subdim, tag_names in subs.items():
            for name in tag_names:
                add_tag(name, KIND_KNOWLEDGE, parent=subdim,
                        meta={"dimension": dim}, source="seed")
                n += 1
    for family, items in exam.LOGIC_CATALOGUE.items():
        for it in items:
            add_tag(it["tag"], KIND_LOGIC, parent=family,
                    description=it.get("move"),
                    meta={"move": it.get("move"), "flaw": it.get("flaw")},
                    source="seed")
            n += 1
    return n
