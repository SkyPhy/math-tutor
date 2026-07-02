"""
User accounts & sessions — SQLite storage.
===========================================
Stores users (with salted PBKDF2-hashed passwords) and login sessions in a
local SQLite database (`users.db`, created on first run). Uses ONLY the Python
standard library — no extra pip dependency, no external DB server.

Security notes:
  • Passwords are never stored in plaintext. Each user gets a random 16-byte
    salt; the hash is PBKDF2-HMAC-SHA256 with 200k iterations.
  • Comparisons use hmac.compare_digest (constant time).
  • Sessions are opaque random tokens (secrets.token_urlsafe) with an expiry.
  • Every query is parameterised (no string interpolation) → no SQL injection.
"""

from __future__ import annotations

import os
import re
import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from . import config

# All persistent data lives in backend/data/ (one level up from this app/
# package), created on first import, so the SQLite files aren't scattered
# through the backend source.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "users.db")

_PBKDF2_ITERATIONS = 200_000
_SESSION_DAYS = 30
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

# ── Brute-force throttle ───────────────────────────────────────────────────
# After _MAX_FAILS failed sign-ins for a username within _FAIL_WINDOW seconds,
# lock further attempts for the rest of the window. In-memory (resets on
# restart) — fine for a single-process demo.
_MAX_FAILS = 5
_FAIL_WINDOW = 300  # seconds (5 min)
_fail_log: Dict[str, list] = {}


# ── Connection / schema ────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    # A fresh connection per call keeps things thread-safe under FastAPI's
    # threadpool. SQLite handles this fine at demo scale.
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Roles ──────────────────────────────────────────────────────────────────
# Only "admin" and "student" exist. Admins are the ONLY accounts allowed to
# toggle model availability / force a model (see model_policy.py + main.py's
# require_admin). Admin usernames are seeded from config.ADMIN_USERNAMES (.env);
# there is deliberately no in-app way for a student to promote themselves.
ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"


def _role_for(username: str) -> str:
    """The role a username should have: admin iff listed in ADMIN_USERNAMES."""
    return ROLE_ADMIN if (username or "") in config.ADMIN_USERNAMES else ROLE_STUDENT


def init_db() -> None:
    """Create the tables if they don't exist, migrate the role column onto older
    DBs, and (re)seed admin roles from ADMIN_USERNAMES. Safe on every startup."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                email         TEXT,
                password_hash TEXT    NOT NULL,
                password_salt TEXT    NOT NULL,
                role          TEXT    NOT NULL DEFAULT 'student',
                created_at    TEXT    NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT    PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                created_at TEXT    NOT NULL,
                expires_at TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        # Migrate: older users.db predates the role column — add it in place.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
        if "role" not in cols:
            conn.execute(
                "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")
        # Seed / refresh admin roles from .env every startup so the configured
        # admins are always admins (and only they). Students are left untouched.
        if config.ADMIN_USERNAMES:
            placeholders = ",".join("?" for _ in config.ADMIN_USERNAMES)
            conn.execute(
                f"UPDATE users SET role = '{ROLE_ADMIN}' "
                f"WHERE username IN ({placeholders})",
                tuple(config.ADMIN_USERNAMES),
            )
        conn.commit()


# ── Password hashing ───────────────────────────────────────────────────────
def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return dk.hex()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _throttle_check(username: str) -> None:
    """Raise AuthError(429) if too many recent failures for this username."""
    import time
    now = time.time()
    hits = [t for t in _fail_log.get(username, []) if now - t < _FAIL_WINDOW]
    _fail_log[username] = hits
    if len(hits) >= _MAX_FAILS:
        wait = int(_FAIL_WINDOW - (now - hits[0]))
        raise AuthError(
            f"Too many failed attempts. Try again in {max(wait, 1)} seconds.", 429
        )


def _throttle_record_fail(username: str) -> None:
    import time
    _fail_log.setdefault(username, []).append(time.time())


def _throttle_clear(username: str) -> None:
    _fail_log.pop(username, None)


# ── Public API ─────────────────────────────────────────────────────────────
class AuthError(Exception):
    """Raised for any auth failure with a user-safe message + HTTP-ish code."""

    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code


def _public_user(row: sqlite3.Row) -> Dict[str, Any]:
    """User fields safe to send to the client (never the hash/salt). `role` lets
    the frontend decide whether to show the admin-only model controls."""
    keys = row.keys()
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": (row["role"] if "role" in keys else ROLE_STUDENT) or ROLE_STUDENT,
        "created_at": row["created_at"],
    }


def is_admin(user: Optional[Dict[str, Any]]) -> bool:
    """True when `user` (a _public_user dict) carries the admin role."""
    return bool(user and user.get("role") == ROLE_ADMIN)


def sign_up(username: str, password: str, email: Optional[str] = None) -> Dict[str, Any]:
    """Create a new account and open a session. Returns {user, token}."""
    username = (username or "").strip()
    email = (email or "").strip() or None

    if not _USERNAME_RE.match(username):
        raise AuthError(
            "Username must be 3–32 characters: letters, numbers, . _ -", 400
        )
    if len(password or "") < 6:
        raise AuthError("Password must be at least 6 characters.", 400)
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise AuthError("Please enter a valid email address.", 400)

    salt = secrets.token_bytes(16)
    pw_hash = _hash_password(password, salt)
    created = _now().isoformat()

    try:
        with _connect() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, email, password_hash, password_salt, role, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, email, pw_hash, salt.hex(), _role_for(username), created),
            )
            user_id = cur.lastrowid
            conn.commit()
    except sqlite3.IntegrityError:
        raise AuthError("That username is already taken.", 409)

    token = _open_session(user_id)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"user": _public_user(row), "token": token}


def sign_in(username: str, password: str) -> Dict[str, Any]:
    """Validate credentials and open a session. Returns {user, token}.
    Throttles repeated failures to blunt brute-force/credential-stuffing."""
    username = (username or "").strip()
    _throttle_check(username)

    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

    # Always compute a hash to keep timing roughly constant for unknown users.
    if row is None:
        _hash_password(password or "", b"dummy-salt-000000")
        _throttle_record_fail(username)
        raise AuthError("Incorrect username or password.", 401)

    salt = bytes.fromhex(row["password_salt"])
    candidate = _hash_password(password or "", salt)
    if not hmac.compare_digest(candidate, row["password_hash"]):
        _throttle_record_fail(username)
        raise AuthError("Incorrect username or password.", 401)

    _throttle_clear(username)
    token = _open_session(row["id"])
    return {"user": _public_user(row), "token": token}


def sign_out(token: str) -> None:
    """Invalidate a session token (no error if it doesn't exist)."""
    if not token:
        return
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Return the public user for a valid, unexpired session token, else None."""
    if not token:
        return None
    with _connect() as conn:
        sess = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        if sess is None:
            return None
        # Expired? clean it up and reject.
        try:
            expires = datetime.fromisoformat(sess["expires_at"])
        except ValueError:
            expires = _now() - timedelta(seconds=1)
        if expires < _now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (sess["user_id"],)
        ).fetchone()
        return _public_user(row) if row else None


def _open_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now.isoformat(), (now + timedelta(days=_SESSION_DAYS)).isoformat()),
        )
        conn.commit()
    return token


def user_count() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
