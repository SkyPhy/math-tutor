# Codex Notes

This folder stores my working understanding of the `math-tutor` codebase so we can
move faster in later development turns.

## Current baseline

- Repo: `SkyPhy/math-tutor`
- Current uncommitted feature wave: `v0.4.12a`
- Theme of the latest update:
  - multi-provider LLM support (`Claude`, `DeepSeek`, `GPT`)
  - admin-controlled student model pool
  - optional forced model assignment
  - DeepSeek OCR path

## Read order for future work

1. `backend.md`
2. `frontend.md`

## High-level architecture

- `backend/`
  - FastAPI app
  - orchestration-heavy `app/main.py`
  - SQLite-backed product state (`users`, `exams`, `tags`, `workspace`, `diagnosis`, `memory`, `model_policy`)
  - LLM/OCR/provider logic split into dedicated modules
- `frontend/`
  - Vite + React + TypeScript
  - five-screen tutor flow
  - one global store for navigation, whiteboard, handoff state, and chosen model

## Recent update summary

- Backend is no longer Claude-only. Model resolution now goes through:
  - `config.py` -> provider config
  - `providers.py` -> catalog + pool + forced resolution
  - `model_policy.py` -> runtime admin overlay
  - `claude_service.py` -> actual transport dispatch by protocol
- Frontend now exposes:
  - student model picker in the global header
  - admin-only model management panel behind login
  - selected model propagated into generation, grading, assistant, and chat calls

## Practical dev reminders

- Real secrets live in `backend/.env` and must stay out of git.
- `backend/.env.example` is safe to commit.
- `main.py` still contains a lot of product logic; new work should prefer extracting logic into focused modules when possible.
- The best backend-first path for future work is:
  - trace endpoint in `main.py`
  - find delegated module
  - inspect matching frontend call in `frontend/src/api.ts`
  - then inspect the screen/component that consumes it
