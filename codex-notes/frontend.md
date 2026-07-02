# Frontend Notes

## Entry chain

- `src/main.tsx`
  - mounts `StoreProvider` and `App`
- `src/App.tsx`
  - global header controls
  - renders the five tutor screens

## Core mental model

The frontend is a five-screen guided workflow with one shared global store.
Screen-specific state stays local; cross-screen state lives in `store.tsx`.

## Global store

- File: `src/store.tsx`
- Owns:
  - current screen and back-stack
  - workflow mode (`submit` or `assist`)
  - persistent Excalidraw board instance
  - current problem
  - OCR handoff text
  - corrected student work
  - render mode
  - selected model list and current model
  - forced model state
  - generated `sessionId`

## API boundary

- File: `src/api.ts`
- Rule of thumb:
  - screens and components should call typed helpers here
  - backend endpoint shapes are centralized here

## Main screens

### `ProblemScreen`

- fetches problems from `/practice/next`
- owns source choice and practice controls
- starts either submit flow or assistant flow

### `SelectScreen`

- crops/lassos whiteboard snapshot
- sends selected region to `/recognize`

### `CheckScreen`

- edits OCR text
- supports render modes
- saves drafts via `/work/save`
- grades via `/verify`

### `AssistantScreen`

- sends corrected work to `/assistant/analyze`
- shows aligned line-by-line feedback
- sends focused follow-up questions to `/assistant/ask`

### `AskScreen`

- free-form question answering on the current problem
- uses `/claude/chat`
- can also call `/analyze` for a tutor-style read of the problem

## New model-selection UI

- `components/ModelControls.tsx`
  - student-facing model picker in the header
  - locked when backend returns `forced_model`
- `components/AdminModels.tsx`
  - admin-only model management panel
  - signs in through `/auth/signin`
  - reads and mutates `/admin/models`

## Styling and docs

- all styling is centralized in `src/styles.css`
- project-specific frontend conventions live in `docs/FRONTEND_GUIDE.md`

## Frontend-second debugging recipe

1. Start from the visible screen.
2. Find the matching API helper in `api.ts`.
3. Confirm store inputs:
   - `problem`
   - `studentWork`
   - `renderMode`
   - `model`
   - `sessionId`
4. Then verify the backend route and delegated module.

## Latest feature wave to remember

- Model choice is now a first-class part of the UX.
- Student model choice is still constrained by the backend pool.
- Admin model control is intentionally separate from the normal student flow.
