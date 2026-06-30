# AI Math Tutor

A Socratic (guided, never answer-dumping) AI math tutoring system for primary-school
mathematics. A **FastAPI** backend pairs **Claude** (natural-language reasoning & tutoring)
with a **vision OCR** model for handwriting; the student-facing UI is a **Vite + React + TS**
app (`frontend/`) providing the whiteboard, chat, and the guided five-screen tutor flow.

> **★ Frontend re-platform (v0.4).** The core student tutor moved from a single static
> `web/demo_standalone.html` to a maintainable, config-driven **React app under `frontend/`**.
> The **backend is unchanged** — React calls the same FastAPI endpoints over HTTP. The old
> static pages are archived under [`web/legacyweb/`](web/legacyweb/). Run the frontend with
> `cd frontend && npm install && npm run dev` (see [`frontend/README.md`](frontend/README.md)).

> **★ Direction (realized): verification by consensus, not by CAS.** Grading's source of
> truth is now **multi-path LLM consensus** (`backend/app/reasoner.py`) — the same problem is
> solved several independent ways and the majority answer wins. SymPy has been retired to
> `backend/app/legacy/sympy_grader.py` as a non-authoritative offline fallback (it still
> renders steps/plots for `/analyze`·`/hint`·`/animate`·`/plot`). See
> [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) §4.

> **New here / taking over the project?** Read [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md)
> (architecture + roadmap, kept current) and the [root `CHANGELOG.md`](CHANGELOG.md) (every
> version, newest first). The earlier `DEVELOPMENT_LOG.md` / `HANDOFF.md` snapshots are
> **archived** under [`docs/legacy/`](docs/legacy/) (`*.od.md` = outdated, history only).

## Core principles
- **Verification by consensus, not by CAS** — grading's source of truth is multi-path LLM
  consensus (`reasoner.py`): the same problem is solved several independent ways and the
  majority answer wins. SymPy is a non-authoritative offline fallback only.
- **Logic-thinking-type training (the v2.0 differentiator)** — questions are tagged on two
  orthogonal axes — knowledge point × logic-thinking type — plus an open-ended difficulty
  (1 = 认识数字 … 10 = 大学通识, higher allowed). Practice adapts to a student's weakest
  *logic type*, not just weak knowledge points. The tag vocabulary is self-evolving (the AI
  can add/remove tags at runtime; stored in `tags.db`).
- **Socratic constraint** — the tutor gives graduated hints (5 levels), never the final
  answer up front.
- **Graceful degradation** — with no API keys configured, the tutor falls back to a
  template engine and OCR returns a mock, so the app always runs.

## Architecture
```
math/
├── README.md  CHANGELOG.md  .gitignore
├── backend/                      Backend — FastAPI
│   ├── app/                      Python package (run as app.main:app)
│   │   ├── main.py               Routes + core engines (Socratic, Policy, rendering, providers)
│   │   ├── reasoner.py           Multi-path LLM consensus — grading source of truth
│   │   ├── config.py             .env loader + Claude/OCR/Xueke settings (the ONLY secrets reader)
│   │   ├── claude_service.py     Claude gateway client (timeout / circuit-breaker / rate-limit)
│   │   ├── recognize.py          Handwriting OCR (nex-n2-pro vision; + Claude-vision path)
│   │   ├── prompts.py            Claude system prompts (Socratic / chat / generation / solve)
│   │   ├── exam.py               SQLite question bank + catalogue + structured numbering
│   │   ├── tags.py               Self-evolving tag vocabulary (tags.db; AI-managed)
│   │   ├── diagnosis.py          Logic-flaw diagnosis (student + AI-self consensus signals)
│   │   ├── memory.py             Persistent experience memory (memory.db)
│   │   ├── auth.py               Accounts / sessions (SQLite, PBKDF2)
│   │   └── legacy/sympy_grader.py  Retired SymPy grader — non-authoritative offline fallback
│   ├── requirements.txt
│   ├── test_reasoner_offline.py  Offline regression for the consensus normaliser (no gateway)
│   ├── .env.example              Template — copy to .env and fill in keys
│   ├── .env                      Your real keys (gitignored, never committed)
│   └── data/                     SQLite DBs (users/exams/tags/diagnosis/memory.db) — gitignored
├── frontend/                     Student tutor — Vite + React + TypeScript (run: npm run dev)
│   ├── index.html                Vite entry (loads MathJax + the React app)
│   ├── package.json  vite.config.ts  tsconfig.json
│   └── src/                      App, config (SCREEN_DEFS/SOURCES/ACTIONS), api client,
│                                 store (5-screen router), board/BoardEngine, screens/, components/
├── web/                          Legacy static frontend (archived; see frontend/ for the live app)
│   ├── legacyweb/                Old static pages — index / signin / signup / sellection /
│   │                            exam / standalone (moved here in v0.4.0a, kept runnable)
│   └── legacy/                   Earlier React/Vite prototype + demo_standalone.v0.2.html backup
├── docs/                         DEVELOPMENT_PLAN, LOGIC_TAXONOMY, design/ (blueprint),
│   └── legacy/                   Archived docs (HANDOFF.od.md, DEVELOPMENT_LOG.od.md)
└── lesson/README.md              Knowledge-point taxonomy (exam data source)
```

## Prerequisites
- **Python 3.12** (run with `py -3.12` on this setup)
- Dependencies: `fastapi`, `uvicorn`, `sympy`, `python-multipart`, `pillow`
  (standard library otherwise — no EasyOCR/Torch, no python-dotenv, no Anthropic SDK)

## Setup

### 1. Install dependencies
```bash
py -3.12 -m pip install -r backend/requirements.txt
```

### 2. Configure keys (secrets live in ONE gitignored file)
All API keys live only in `backend/.env`, which is **never committed**. Every module
reads them through `backend/app/config.py` — no key is ever hard-coded in source.
Create your own `.env` from the template:
```bash
cp backend/.env.example backend/.env
# then edit backend/.env and fill in:
#   CLAUDE_*    — an Anthropic-compatible gateway for the AI tutor (chat + hints + exam)
#   NEX_OCR_*   — an OpenAI-compatible vision model (nex-n2-pro) for handwriting OCR
```
Leave them blank to run in fallback mode (template tutor + mock OCR). `.env` and
`backend/data/` are listed in `.gitignore`, so keys and the local DBs stay off GitHub.

### 3. Start the backend
**Run from the `backend/` directory** (the app is a package, `app.main:app`):
```bash
cd backend
py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
On startup it prints health lines for the OCR gateway, user DB, and exam bank.

### 4. Start the frontend
```bash
cd frontend
npm install
npm run dev          # Vite dev server → http://localhost:5173
```
It calls the backend at `http://localhost:8000` (override with `VITE_API_BASE`). The archived
static pages still open directly from `web/legacyweb/` if you need them.

## Features
- **Whiteboard** — draw on the native canvas or Excalidraw (switchable), with fullscreen.
- **Handwriting OCR** — submit the board; `nex-n2-pro` transcribes it (`/recognize`). A
  Claude-vision path (`?method=claude`/`auto`) is available as an alternative/fallback.
- **Consensus grading** — `/verify` grades answers by multi-path LLM consensus (`reasoner.py`),
  returning `judged_by` (e.g. `consensus(3/3)`), `agreement`, and the consensus `ground_truth`.
- **Self-evolving question feed** — `/practice/next` serves from three sources: AI generation
  (Claude), the local bank by tag, or the 学科网 API. AI-generated questions carry a
  "请注意甄别" disclaimer; every saved question gets a structured id (`{source}-{date}-{seq}`).
- **Logic diagnosis & adaptive practice** — tracks each student's weakest *logic-thinking type*
  (and the AI's own consensus-divergence) and generates targeted questions (`?adaptive=<sid>`).
- **Socratic hints** — 5 graduated levels, AI-generated (Claude) with template fallback.
- **AI chat** — discuss a problem with a selectable Claude model.
- **Auto exam** — generates a question for every knowledge point (taxonomy from
  [`lesson/README.md`](lesson/README.md)), tagged with logic types + difficulty, stored in
  SQLite and tag-indexed; tags are hidden behind a per-question button.
- **Accounts** — sign up / sign in / sign out (SQLite, PBKDF2-hashed passwords). Optional —
  the demo works without logging in.

## Student UI — five-screen guided flow (React, in progress)
The core tutor is a **five-screen guided flow**, now built in `frontend/` (React + TS). Spec,
navigation state machine, and the backend it needs live in
[`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) §"v0.3 学生端「试卷测试」多屏交互重构".
- **Screens**: ① problem (source picker AI/学科网/bank · tags toggle · whiteboard) → ② select
  (lasso/crop the strokes to send · pick OCR model) → ③ check (OCR review + correct, 3 render
  modes, save draft) → ④ AI assistant (line-by-line answer ↔ analysis, `<manim>` viz, per-line
  follow-up) and ⑤ ask (Q&A for "I'm stuck", no whiteboard).
- **Status (v0.4.0a)**: scaffolded the React app; **screen ① is wired** (source → `/practice/next`,
  MathJax problem card, native whiteboard, targeted practice, 3 actions). Screens ②–⑤ are honest
  stubs that name their endpoints; the real interactions land in **v0.4.1a → v0.4.4a**.
- **Reuses** today's endpoints (`/practice/next`, `/recognize`, `/verify`, `/claude/chat`,
  `/analyze`, `/animate`); **adds** `/recognize/models`, `/work/*` (personal draft DB,
  `workspace.py`), `/assistant/analyze` + `/assistant/ask` (`assistant.py`), and a phased real
  Manim render (`/manim/render`).
- **Migration rule**: before any full rewrite, the old files are archived (never deleted) —
  the static pages now live under [`web/legacyweb/`](web/legacyweb/).

## Notes & known issues
- **OCR / exam generation can be slow (20–50s+)** — the shared gateway is latency-prone;
  the UI shows a spinner. See [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) §5
  (gateway resilience) for details.
- `nex-n2-pro` is a reasoning model — `NEX_OCR_MAX_TOKENS` is kept generous and thinking
  is disabled for OCR (see `backend/app/recognize.py`).
- CORS is open (`*`), so opening the HTML directly from disk works.
- `web/legacy/` is the **abandoned** React/Vite prototype, kept for reference only. The
  live app is `backend/app/` + the static pages in `web/`.

## Troubleshooting
- **`Could not import module "app.main"`** — start uvicorn from inside `backend/`.
- **Tutor/OCR returns fallback/mock** — `.env` isn't configured or the gateway is unreachable.
- **Backend unreachable** — confirm uvicorn is running on port 8000.
