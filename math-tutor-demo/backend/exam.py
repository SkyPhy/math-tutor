"""
Exam question bank — generation catalogue + SQLite storage.
============================================================
Backs the demo_exam.html page. Two responsibilities:

  1. CATALOGUE — the knowledge-point taxonomy from lesson/README.md, organised
     as TWO dimensions (the two tables), each with sub-dimensions (维度) that
     hold the actual knowledge-point TAGS. "Cover all types" = produce at least
     one question per tag across both dimensions.

  2. STORAGE — a SQLite question bank (`exams.db`) where each question carries
     tags across the two dimensions (a question may have MANY tags in a
     dimension). A `question_tags` table indexed on (dimension, tag) lets us
     find every question of a given type immediately.

Standard library only (sqlite3) — no extra dependency.
"""

from __future__ import annotations

import os
import sqlite3
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Persistent data lives in the shared `data/` directory (see auth.py).
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "exams.db")

DIM_CORE = "核心知识领域"
DIM_METHOD = "综合与思想方法"

# ── The taxonomy (from lesson/README.md) ───────────────────────────────────
#   dimension → sub-dimension (维度) → [knowledge-point tags]
CATALOGUE: Dict[str, Dict[str, List[str]]] = {
    DIM_CORE: {
        "数与代数": ["数的认识", "数的运算", "数的关系", "初步代数思想"],
        "图形与几何": ["平面图形", "立体图形", "图形的变换", "位置与方向"],
        "量与计量": ["长度", "面积、体积、容积", "质量", "时间", "货币"],
        "统计与概率": ["数据收集与整理", "统计图", "平均数、中位数、众数", "可能性"],
    },
    DIM_METHOD: {
        "综合与实践": ["跨学科应用", "数学活动、项目式学习", "建模意识与应用能力"],
        "数学思想方法": ["数感、符号意识、空间观念", "推理能力（归纳、演绎）", "模型思想",
                    "数据分析观念", "应用意识与创新意识"],
    },
}


def all_tags() -> List[Dict[str, str]]:
    """Flat list of every tag with its dimension + sub-dimension."""
    out = []
    for dim, subs in CATALOGUE.items():
        for subdim, tags in subs.items():
            for tag in tags:
                out.append({"dimension": dim, "subdimension": subdim, "tag": tag})
    return out


def tag_dimension(tag: str) -> Optional[str]:
    for dim, subs in CATALOGUE.items():
        for tags in subs.values():
            if tag in tags:
                return dim
    return None


def tag_subdimension(tag: str) -> Optional[str]:
    for subs in CATALOGUE.values():
        for subdim, tags in subs.items():
            if tag in tags:
                return subdim
    return None


# ── Template question bank (deterministic fallback, one per tag) ───────────
# Guarantees full coverage instantly when the AI is slow/unavailable.
# tag -> (statement, latex, answer)
TEMPLATES: Dict[str, tuple] = {
    # 数与代数
    "数的认识": ("把下面各数从小到大排列。", "1203,\\ 1320,\\ 1032,\\ 1230", "1032 < 1203 < 1230 < 1320"),
    "数的运算": ("计算下面各题。", "256 + 178 - 95", "339"),
    "数的关系": ("求 18 和 24 的最大公因数。", "\\gcd(18,\\ 24)", "6"),
    "初步代数思想": ("解方程，求 x 的值。", "3x + 7 = 22", "x = 5"),
    # 图形与几何
    "平面图形": ("一个长方形长 8 cm，宽 5 cm，求它的周长。", "C = 2\\times(8+5)", "26 cm"),
    "立体图形": ("一个正方体的棱长是 4 cm，求它的体积。", "V = 4^3", "64 cm³"),
    "图形的变换": ("把一个三角形向右平移 5 格，说出平移的方向和距离。", "", "向右平移 5 格"),
    "位置与方向": ("用数对表示：点 A 在第 3 列第 2 行。", "(3,\\ 2)", "(3, 2)"),
    # 量与计量
    "长度": ("把 3 米 5 厘米换算成厘米。", "3\\,m\\,5\\,cm = ?\\,cm", "305 cm"),
    "面积、体积、容积": ("一个正方形边长 6 dm，求它的面积。", "S = 6^2", "36 dm²"),
    "质量": ("填空：3 千克 = ( ) 克。", "3\\,kg = ?\\,g", "3000 g"),
    "时间": ("从 8:15 到 9:40 经过了多长时间？", "", "1 小时 25 分"),
    "货币": ("买一支笔 3 元 5 角，付出 10 元，应找回多少钱？", "10 - 3.5", "6.5 元"),
    # 统计与概率
    "数据收集与整理": ("说出整理一组调查数据的步骤。", "", "收集 → 分类 → 计数 → 制表"),
    "统计图": ("要表示一天气温的变化，应选择哪种统计图？", "", "折线统计图（反映变化趋势）"),
    "平均数、中位数、众数": ("求下面一组数据的平均数：5, 8, 6, 9, 7。", "\\bar{x}=(5+8+6+9+7)\\div5", "7"),
    "可能性": ("盒子里有 3 个红球、1 个白球，任意摸一个，摸到红球的可能性是多少？", "P=\\frac{3}{4}", "3/4"),
    # 综合与实践
    "跨学科应用": ("设计一次班级义卖，列出估算盈利需要的数据。", "", "成本、售价、数量、利润（开放题）"),
    "数学活动、项目式学习": ("计算教室地面铺边长 50 cm 的方砖需要多少块。", "", "地面面积 ÷ 每块面积（开放题）"),
    "建模意识与应用能力": ("用一个式子表示：每本书 a 元，买 5 本共付多少钱？", "5a", "5a 元"),
    # 数学思想方法
    "数感、符号意识、空间观念": ("估一估：298 × 3 大约是多少？", "298\\times3", "约 900"),
    "推理能力（归纳、演绎）": ("找规律填数：2, 4, 8, 16, ( )。", "2,\\ 4,\\ 8,\\ 16,\\ ?", "32"),
    "模型思想": ("用字母表示长方形的周长公式。", "C = 2(a+b)", "C = 2(a+b)"),
    "数据分析观念": ("根据统计表分析：哪个月销量最高，并说明理由。", "", "读图比较（开放题）"),
    "应用意识与创新意识": ("设计一个家庭节水方案，并估算每月节水量。", "", "建模估算（开放题）"),
}


def template_question(tag: str) -> Dict[str, Any]:
    """A deterministic question for a tag, tagged on its own dimension."""
    statement, latex, answer = TEMPLATES.get(
        tag, (f"请解答与「{tag}」相关的一道题。", "", "（开放题）")
    )
    dim = tag_dimension(tag) or DIM_CORE
    subdim = tag_subdimension(tag) or ""
    return {
        "statement": statement,
        "latex": latex,
        "answer": answer,
        "grade": None,
        "source": "template",
        "tags": [{"dimension": dim, "subdimension": subdim, "tag": tag, "primary": True}],
    }


# ── SQLite storage ─────────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id         TEXT PRIMARY KEY,
                statement  TEXT NOT NULL,
                latex      TEXT,
                answer     TEXT,
                grade      INTEGER,
                source     TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS question_tags (
                question_id  TEXT NOT NULL,
                dimension    TEXT NOT NULL,
                subdimension TEXT,
                tag          TEXT NOT NULL,
                is_primary   INTEGER DEFAULT 0,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
            """
        )
        # Index so "find every question of this type" is an immediate lookup.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_qtags_dim_tag ON question_tags(dimension, tag)"
        )
        conn.commit()


def _new_id() -> str:
    return "q-" + secrets.token_hex(5)


def save_question(q: Dict[str, Any]) -> str:
    """Persist a question + its tags. Returns the new id."""
    qid = _new_id()
    created = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO questions (id, statement, latex, answer, grade, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (qid, q.get("statement", ""), q.get("latex", ""), q.get("answer", ""),
             q.get("grade"), q.get("source", "ai"), created),
        )
        for t in q.get("tags", []):
            conn.execute(
                "INSERT INTO question_tags (question_id, dimension, subdimension, tag, is_primary) "
                "VALUES (?, ?, ?, ?, ?)",
                (qid, t["dimension"], t.get("subdimension", ""), t["tag"],
                 1 if t.get("primary") else 0),
            )
        conn.commit()
    return qid


def _tags_for(conn: sqlite3.Connection, qid: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT dimension, subdimension, tag, is_primary FROM question_tags WHERE question_id = ?",
        (qid,),
    ).fetchall()
    return [
        {"dimension": r["dimension"], "subdimension": r["subdimension"],
         "tag": r["tag"], "primary": bool(r["is_primary"])}
        for r in rows
    ]


def _assemble(conn: sqlite3.Connection, row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "statement": row["statement"],
        "latex": row["latex"],
        "answer": row["answer"],
        "grade": row["grade"],
        "source": row["source"],
        "created_at": row["created_at"],
        "tags": _tags_for(conn, row["id"]),
    }


def list_questions(limit: int = 500) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM questions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_assemble(conn, r) for r in rows]


def find_by_tag(tag: str, dimension: Optional[str] = None) -> List[Dict[str, Any]]:
    """Immediate lookup: every question carrying this tag (optionally scoped to
    a dimension). Uses the (dimension, tag) index."""
    with _connect() as conn:
        if dimension:
            ids = conn.execute(
                "SELECT DISTINCT question_id FROM question_tags WHERE dimension = ? AND tag = ?",
                (dimension, tag),
            ).fetchall()
        else:
            ids = conn.execute(
                "SELECT DISTINCT question_id FROM question_tags WHERE tag = ?", (tag,)
            ).fetchall()
        out = []
        for r in ids:
            row = conn.execute("SELECT * FROM questions WHERE id = ?", (r["question_id"],)).fetchone()
            if row:
                out.append(_assemble(conn, row))
        return out


def find_by_dimension(dimension: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        ids = conn.execute(
            "SELECT DISTINCT question_id FROM question_tags WHERE dimension = ?", (dimension,)
        ).fetchall()
        out = []
        for r in ids:
            row = conn.execute("SELECT * FROM questions WHERE id = ?", (r["question_id"],)).fetchone()
            if row:
                out.append(_assemble(conn, row))
        return out


def coverage() -> Dict[str, Any]:
    """Which catalogue tags have ≥1 question in the bank."""
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT tag FROM question_tags").fetchall()
    covered = {r["tag"] for r in rows}
    everything = [t["tag"] for t in all_tags()]
    return {
        "covered": sorted(t for t in everything if t in covered),
        "missing": [t for t in everything if t not in covered],
        "covered_count": sum(1 for t in everything if t in covered),
        "total": len(everything),
    }


def bank_size() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM questions").fetchone()["n"]
