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

# Persistent data lives in the shared backend/data/ directory (see auth.py),
# one level up from this app/ package.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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


# ── v2.0 core differentiator: logic-thinking-type taxonomy ──────────────────
#   ORTHOGONAL to the knowledge-point CATALOGUE above. A question carries BOTH
#   its knowledge tags AND logic-type tags + a difficulty rung. The same logic
#   type (e.g. 逆向倒推) can appear on any knowledge point. Design + rationale +
#   the student logic-flaw each tag diagnoses: see docs/LOGIC_TAXONOMY.md.
#   NOTE: DRAFT taxonomy — the categories are a product decision, refine freely.
#   This block is purely ADDITIVE: nothing below the knowledge-point flow calls
#   it yet (generation/diagnosis wiring is a later, reviewed step).
DIM_LOGIC = "逻辑思维类型"

# Difficulty ladder — OPEN-ENDED (no hard upper limit). Difficulty COMBINES the
# knowledge-content level AND the logic-thinking difficulty: a problem with an
# easy knowledge point but a hard thinking type (倒推/假设/分类讨论…) ranks higher
# than its content level alone. Anchored by the user: 1 = 认识数字 (most basic),
# 10 = 大学通识课; values ABOVE 10 are valid (olympiad/research). The labels below
# are content-level guides, not grade bindings. Distinct from questions.grade.
DIFFICULTY_MIN = 1
DIFFICULTY_LEVELS: Dict[int, str] = {
    1: "认识数字 · 数物体、认读数（最基础）",
    2: "低年级 · 20 以内加减、直观单步",
    3: "低年级 · 百以内运算 / 简单两步",
    4: "中年级 · 两步、引入解题策略",
    5: "中年级 · 多步、需选择策略",
    6: "高年级 · 分数/比例、抽象关系",
    7: "高年级 · 多步多策略组合",
    8: "初中过渡 · 代数化、形式化推理",
    9: "高中 / 竞赛初步 · 多策略嵌套",
    10: "大学通识课 · 抽象建模、严密论证",
}

#   family (subdimension) → [ {tag, move, flaw} ]
#     move = 这类题在练的思维动作；flaw = 学生在这类上的典型逻辑缺陷（诊断信号）
LOGIC_CATALOGUE: Dict[str, List[Dict[str, str]]] = {
    "推理模式": [
        {"tag": "归纳推理", "move": "从特例发现规律并推广到一般", "flaw": "只盯个例不会概括；据少数例错误归纳"},
        {"tag": "演绎推理", "move": "由已知条件按规则逐步推出结论", "flaw": "跳步、漏用条件、因果倒置"},
        {"tag": "类比迁移", "move": "把新问题映射到已掌握的模型", "flaw": "迁移错位；想不起可联系的旧知"},
    ],
    "策略与转化": [
        {"tag": "逆向倒推", "move": "从结果反向还原每一步", "flaw": "只会顺推、不会用逆运算还原"},
        {"tag": "假设调整", "move": "先假设一种情形再按差异修正（鸡兔同笼）", "flaw": "不会设假设；不会按差量调整"},
        {"tag": "化归转化", "move": "化繁为简、化未知为已知", "flaw": "被表象困住，找不到等价的简单形式"},
        {"tag": "整体思想", "move": "把一组量作为整体处理而非逐个", "flaw": "纠缠局部、看不到整体关系"},
    ],
    "结构化枚举": [
        {"tag": "分类讨论", "move": "按互斥且穷尽的标准分情况", "flaw": "漏情况、重复；分类标准混乱"},
        {"tag": "有序枚举", "move": "有序、不重不漏地列出所有可能", "flaw": "无序乱列、漏数或重数"},
    ],
    "表征建图": [
        {"tag": "数形结合", "move": "用线段图/示意图表征数量关系", "flaw": "不会画图、读不懂图；图意与题意不符"},
        {"tag": "列表对应", "move": "用表格/一一对应整理信息", "flaw": "信息散乱、对应错位"},
    ],
    "建模与估计": [
        {"tag": "方程建模", "move": "设未知数、列等量关系求解", "flaw": "不会设元；等量关系列错"},
        {"tag": "估算逼近", "move": "用上下界/近似判断结果合理性", "flaw": "缺数感；不检验结果是否合理"},
    ],
}


def all_logic_tags() -> List[Dict[str, str]]:
    """Flat list of every logic-type tag with its family + move + flaw."""
    out = []
    for family, items in LOGIC_CATALOGUE.items():
        for it in items:
            out.append({"dimension": DIM_LOGIC, "family": family,
                        "tag": it["tag"], "move": it["move"], "flaw": it["flaw"]})
    return out


def logic_tag_family(tag: str) -> Optional[str]:
    for family, items in LOGIC_CATALOGUE.items():
        if any(it["tag"] == tag for it in items):
            return family
    return None


def logic_tag_info(tag: str) -> Optional[Dict[str, str]]:
    """Family + thinking-move + diagnosed logic-flaw for one logic-type tag."""
    for family, items in LOGIC_CATALOGUE.items():
        for it in items:
            if it["tag"] == tag:
                return {"dimension": DIM_LOGIC, "family": family,
                        "tag": tag, "move": it["move"], "flaw": it["flaw"]}
    return None


def difficulty_label(level: int) -> str:
    """Anchor description for a difficulty rung. The ladder is OPEN-ENDED:
    values above the top anchor (10) are valid (olympiad / research-level)."""
    if level in DIFFICULTY_LEVELS:
        return DIFFICULTY_LEVELS[level]
    if level > max(DIFFICULTY_LEVELS):
        return f"竞赛 / 研究级（难度 {level}）"
    return ""


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
        # Small key→int store for the global question sequence (题号 SEQ counter).
        conn.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER NOT NULL)"
        )
        # Migration: add the difficulty column to older banks that predate it
        # (logic-type + difficulty is the v2.0 core need). Old rows stay NULL.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(questions)").fetchall()}
        if "difficulty" not in cols:
            conn.execute("ALTER TABLE questions ADD COLUMN difficulty INTEGER")
        conn.commit()


# ── Question numbering (用户规范) ───────────────────────────────────────────
# Structured, parseable id:  {SOURCE}-{YYYYMMDD}-{SEQ}   e.g. 300-20250416-000123
#   • SOURCE — a 3-digit code identifying who produced the question.
#   • DATE   — UTC date of creation (matches created_at), so ids sort by day.
#   • SEQ    — a GLOBAL auto-incrementing counter (1 → ∞), zero-padded to 6 for
#     sortability; it just grows past 6 digits once it overflows ("到无穷").
# A question pulled at random from the EXISTING bank keeps its original id — only
# freshly-created (AI / 学科网 / template) questions are assigned a new number.
SOURCE_CODES: Dict[str, str] = {
    "ai": "300",        # AI 生成（Claude）
    "xueke": "200",     # 学科网 API
    "template": "100",  # 本地模板 / 种子题
    "seed": "100",
}
DEFAULT_SOURCE_CODE = "000"  # 其它 / 未知来源


def source_code(source: Optional[str]) -> str:
    """3-digit code for a question source (`ai`→300, `xueke`→200, …)."""
    return SOURCE_CODES.get((source or "").strip().lower(), DEFAULT_SOURCE_CODE)


def _next_seq(conn: sqlite3.Connection) -> int:
    """Atomically bump and return the global question sequence within `conn`'s
    transaction (one SEQ per saved question, monotonically increasing)."""
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('q_seq', 1) "
        "ON CONFLICT(key) DO UPDATE SET value = value + 1"
    )
    return conn.execute("SELECT value FROM meta WHERE key = 'q_seq'").fetchone()[0]


def _make_id(conn: sqlite3.Connection, source: Optional[str]) -> str:
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{source_code(source)}-{date}-{_next_seq(conn):06d}"


def _new_id() -> str:
    return "q-" + secrets.token_hex(5)


def save_question(q: Dict[str, Any]) -> str:
    """Persist a question + its tags. Returns the new id.

    The id is the structured number `{SOURCE}-{YYYYMMDD}-{SEQ}` (see `_make_id`),
    derived from `q["source"]` so AI questions get a 300-… number, 学科网 a 200-…,
    templates a 100-…. The SEQ is allocated inside this transaction."""
    created = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        qid = _make_id(conn, q.get("source"))
        conn.execute(
            "INSERT INTO questions (id, statement, latex, answer, grade, difficulty, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (qid, q.get("statement", ""), q.get("latex", ""), q.get("answer", ""),
             q.get("grade"), q.get("difficulty"), q.get("source", "ai"), created),
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
        "difficulty": row["difficulty"] if "difficulty" in row.keys() else None,
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


def get_question(qid: str) -> Optional[Dict[str, Any]]:
    """One question (with its tags) by id, or None."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
        return _assemble(conn, row) if row else None


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


def seed_templates() -> int:
    """Populate an EMPTY bank with one deterministic template question per tag so
    the practice feed always has Chinese elementary-math problems — even with no
    gateway/network. No-op (returns 0) when the bank already holds questions."""
    if bank_size() > 0:
        return 0
    n = 0
    for entry in all_tags():
        save_question(template_question(entry["tag"]))
        n += 1
    return n


def random_question(exclude_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """One random question from the EXISTING bank (exams.db), or None if empty.
    `exclude_id` avoids handing back the question currently on screen."""
    qs = list_questions()
    if exclude_id and len(qs) > 1:
        qs = [q for q in qs if q.get("id") != exclude_id]
    if not qs:
        return None
    return secrets.choice(qs)
