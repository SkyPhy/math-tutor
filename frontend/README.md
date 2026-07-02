# Math Tutor — Frontend (Vite + React + TypeScript)

The student-facing tutor UI, re-platformed from the old static `web/demo_standalone.html`
into a maintainable, **config-driven** React app. It implements the v0.3 five-screen guided
flow (① problem → ② select → ③ check → ④ assistant → ⑤ ask) and talks to the **unchanged
FastAPI backend** over HTTP.

> The Python backend (consensus grading `reasoner.py`, diagnosis, self-evolving tags, memory)
> is the correctness core and is **not** part of this rewrite — React only calls it.

> 📖 **Authoritative frontend reference: [`../docs/FRONTEND_GUIDE.md`](../docs/FRONTEND_GUIDE.md)** —
> what every module does, the build standards, the theme/design-token system, and how-to recipes.
> The `Layout` / `Status` sections below are historical and may lag; trust the guide.

## Run

```bash
# 1) start the backend (from repo root)
cd ../backend && py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2) start the frontend (from this folder)
npm install
npm run dev          # Vite dev server on http://localhost:5173
```

The app calls the backend at `http://localhost:8000` by default. Point it elsewhere with an
env var (CORS on the backend is open, so a direct cross-origin call works):

```bash
# frontend/.env.local
VITE_API_BASE=http://localhost:8000
```

A dev proxy for a same-origin `/api` prefix is also configured in `vite.config.ts`.

## Build

```bash
npm run build        # → dist/  (static assets, host anywhere)
npm run preview      # serve the production build locally
npm run typecheck    # tsc --noEmit
```

## Layout

```
src/
├── main.tsx              app entry (mounts <StoreProvider><App/>)
├── App.tsx              global header + the five <section class="screen">
├── styles.css           ported verbatim from the legacy page
├── config.ts            API base + SCREEN_DEFS / SOURCES / PROBLEM_ACTIONS / difficulty ladder
├── types.ts             Problem / Op (strokes) / Tool / BoardMode …
├── api.ts               typed FastAPI client (practice/next, recognize, verify, chat, analyze, tags)
├── store.tsx            React context: screen router + back-stack + board engine + problem
├── board/BoardEngine.ts native canvas engine (strokes[], pen / area-erase / stroke-erase, PNG capture)
├── hooks/useMathJax.ts  typeset a subtree after render
├── components/          ScreenHeader · MathText · ProblemCard · PracticeControls · Whiteboard
└── screens/             ProblemScreen (wired) · Select/Check/Assistant/Ask (stubs → v0.4.1a+)
```

## Status

- **Problem screen** is wired: source picker (AI / 学科网 / 题库 → `/practice/next?source=`),
  tags toggle, MathJax problem card, targeted-practice controls (logic type + difficulty),
  native whiteboard (pen / area-erase / stroke-erase / clear / fullscreen), 3-action row.
- **Screens ②–⑤ are honest stubs** that name the endpoints they will call; the real
  selection / check / line-analysis / Q&A interactions land in v0.4.1a → v0.4.4a (mirroring
  the v0.3.1a–v0.3.4a plan in `docs/DEVELOPMENT_PLAN.md`).
- **Excalidraw** (second board engine) is disabled in the dropdown for this first cut and
  returns in a follow-up (needs Vite-specific config); the native engine is fully working.

The old static pages are archived under [`../web/legacyweb/`](../web/legacyweb/).
