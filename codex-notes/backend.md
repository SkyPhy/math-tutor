# Backend Notes

## Entry point

- Run target: `backend/app/main.py`
- App object: `app = FastAPI(...)`
- Startup hook initializes:
  - OCR availability log
  - auth DB
  - model policy DB
  - exam bank
  - tag store
  - diagnosis DB
  - memory DB
  - workspace DB

## Mental model

`main.py` is still the orchestration hub, but the important subsystems are now
split enough that feature work can usually stay out of the core file after the
route layer.

## Core modules

### Configuration and provider resolution

- `app/config.py`
  - loads `backend/.env`
  - defines provider credentials and model lists
  - holds OCR and Xueke settings
  - exposes helpers like `openai_chat_endpoint()`
- `app/providers.py`
  - builds the full candidate model catalog
  - filters to the student-selectable enabled pool
  - resolves the actual runtime model for each request
- `app/model_policy.py`
  - SQLite runtime overlay for model enable/disable and forced model
  - admin-only control surface

### LLM and reasoning

- `app/claude_service.py`
  - shared text-generation gateway
  - now supports both Anthropic-style and OpenAI-compatible transports
  - keeps per-provider circuit breakers and a per-session rate limiter
- `app/reasoner.py`
  - grading truth path
  - prefers known reference answers when available
  - otherwise uses multi-path LLM consensus
  - SymPy is intentionally not on the grading path
- `app/sympy_compute.py`
  - SymPy survives only as a compute tool for the AI
  - `<sympy>...</sympy>` requests are computed server-side and fed back as `<sympya>...</sympya>`

### Student workflow support

- `app/recognize.py`
  - OCR pipeline
  - engines: `nex`, `deepseek`, `claude`, `auto`
  - preprocesses whiteboard images before sending to vision endpoints
- `app/assistant.py`
  - line-by-line assistant analysis and follow-up chat orchestration
- `app/workspace.py`
  - draft storage for the check screen
- `app/auth.py`
  - users, sessions, roles
  - `admin` role is derived from `ADMIN_USERNAMES`

## Important backend routes

### Model-related

- `GET /models`
  - student-facing selectable model pool
- `GET /claude/models`
  - backward-compatible alias
- `GET /admin/models`
  - admin catalog with usable/enabled flags
- `POST /admin/models`
  - admin mutates enabled flags and forced model

### Student flow

- `GET /practice/next`
  - next problem from bank, AI generation, or Xueke
- `POST /recognize`
  - OCR from selected whiteboard region
- `POST /verify`
  - answer grading
- `POST /assistant/analyze`
  - line-aligned analysis of corrected work
- `POST /assistant/ask`
  - follow-up on a focused line
- `POST /claude/chat`
  - free-form question answering

## Data stores under `backend/data/`

- `users.db`
- `model_policy.db`
- `exams.db`
- `tags.db`
- `diagnosis.db`
- `memory.db`
- `workspace.db`

All of them are local runtime state and should be treated as non-source data.

## Backend-first debugging recipe

1. Find the route in `main.py`.
2. Check whether it delegates to a focused module.
3. Identify whether the call touches:
   - provider selection
   - OCR
   - grading
   - workspace/auth
4. Confirm whether the frontend passes `model`, `session_id`, `question_id`, or `render_mode`.

## Latest feature wave to remember

- Multi-provider LLM support is the main new backend capability.
- Admin control is a product rule, not just a UI detail.
- Students must never gain a path to widen the model pool or override a forced model.
