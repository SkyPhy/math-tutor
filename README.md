# AI Math Tutor

A Socratic (guided, never answer-dumping) AI math tutoring system for primary-school
mathematics. A **FastAPI** backend pairs **SymPy** (deterministic verification) with
**Claude** (natural-language tutoring) and a **vision OCR** model for handwriting; a
**static multi-page frontend** provides the whiteboard, chat, and auto-generated exams.

> **New here / taking over the project?** Read [`docs/HANDOFF.md`](docs/HANDOFF.md) for the
> full factual snapshot, and [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) for the roadmap.

## Core principles
- **SymPy is the verification anchor** — every math result is solved/checked by SymPy;
  Claude only phrases the guidance, it never computes the answer itself.
- **Socratic constraint** — the tutor gives graduated hints (5 levels), never the final
  answer up front.
- **Graceful degradation** — with no API keys configured, the tutor falls back to a
  template engine and OCR returns a mock, so the app always runs.

## Architecture
```
math/
├── README.md  .gitignore
├── backend/                      Backend — FastAPI
│   ├── app/                      Python package (run as app.main:app)
│   │   ├── main.py               Routes + core engines (SymPy, Socratic, Policy, …)
│   │   ├── config.py             .env loader + Claude/OCR settings (the ONLY secrets reader)
│   │   ├── claude_service.py     Claude gateway client (timeout / circuit-breaker)
│   │   ├── recognize.py          Handwriting OCR (nex-n2-pro vision)
│   │   ├── prompts.py            Claude system prompts
│   │   └── auth.py / exam.py     SQLite: accounts/sessions, exam question bank
│   ├── requirements.txt
│   ├── .env.example              Template — copy to .env and fill in keys
│   ├── .env                      Your real keys (gitignored, never committed)
│   └── data/                     SQLite DBs (users.db, exams.db) — gitignored
├── web/                          Frontend — static HTML/CSS/JS (no build step)
│   ├── index.html                Landing page (entry point)
│   ├── signin.html / signup.html Auth pages
│   ├── demo_sellection.html      Pick grade (1–6) + knowledge points
│   ├── demo_exam.html            Auto-generated exam (covers all knowledge points)
│   ├── demo_standalone.html      Core tutor: whiteboard, OCR, chat, hints (+ exam mode)
│   └── legacy/                   Early React/Vite prototype (reference only, not used)
├── docs/                         HANDOFF, DEVELOPMENT_PLAN, design/ (blueprint PDF/MD)
└── lesson/README.md              Knowledge-point taxonomy (exam data source)
```

## Prerequisites
- **Python 3.10+** (developed on 3.14)
- Dependencies: `fastapi`, `uvicorn`, `sympy`, `python-multipart`, `pillow`
  (standard library otherwise — no EasyOCR/Torch, no python-dotenv)

## Setup

### 1. Install dependencies
```bash
pip install -r backend/requirements.txt
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
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
On startup it prints health lines for the OCR gateway, user DB, and exam bank.

### 4. Open the frontend
Open **`web/index.html`** in your browser (static files — no server needed for the
frontend; it calls the backend at `http://localhost:8000`).

## Features
- **Whiteboard** — draw on the native canvas or Excalidraw (switchable), with fullscreen.
- **Handwriting OCR** — submit the board; `nex-n2-pro` transcribes it to an expression.
- **SymPy analysis** — deterministic solving, simplification, classification, step generation.
- **Socratic hints** — 5 graduated levels, AI-generated (Claude) with template fallback.
- **AI chat** — discuss a problem with a selectable Claude model, grounded in the SymPy result.
- **Auto exam** — generates a question for every knowledge point (two-dimension taxonomy
  from [`lesson/README.md`](lesson/README.md)), stored in SQLite and tag-indexed; tags are
  hidden behind a per-question button.
- **Accounts** — sign up / sign in / sign out (SQLite, PBKDF2-hashed passwords). Optional —
  the demo works without logging in.

## Notes & known issues
- **OCR / exam generation can be slow (20–50s+)** — the shared gateway is latency-prone;
  the UI shows a spinner. See [`docs/HANDOFF.md`](docs/HANDOFF.md) §6 for details.
- `nex-n2-pro` is a reasoning model — `NEX_OCR_MAX_TOKENS` is kept generous and thinking
  is disabled for OCR (see `backend/app/recognize.py`).
- CORS is open (`*`), so opening the HTML directly from disk works.
- `web/legacy/` is the **abandoned** React/Vite prototype, kept for reference only. The
  live app is `backend/app/` + the static pages in `web/`.

## Troubleshooting
- **`Could not import module "app.main"`** — start uvicorn from inside `backend/`.
- **Tutor/OCR returns fallback/mock** — `.env` isn't configured or the gateway is unreachable.
- **Backend unreachable** — confirm uvicorn is running on port 8000.
