#!/usr/bin/env bash
# Start math-tutor backend (FastAPI :8000) and frontend (Vite :5173) on macOS/Linux.
# POSIX-side counterpart of start.bat — keeps the project portable across platforms.
#
# Backend runs from a PROJECT-LOCAL venv (backend/.venv) that bundles Manim CE +
# ffmpeg, so /manim/render produces real MP4s. The venv bin dir is prepended to PATH
# so manim_render.available() (shutil.which) finds both. LaTeX (for MathTex/Tex) is
# NOT bundled — install it via your package manager; the app degrades to the browser
# storyboard with a clear message when it's absent (see manim_render.latex_available).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/backend/.venv"
PY="${PYTHON:-python3}"

# --- Bootstrap venv on first run (or if it went missing) ---------------------
if [ ! -x "$VENV/bin/python" ]; then
  echo "[setup] Creating backend venv + installing deps (first run, may take a few minutes)..."
  "$PY" -m venv "$VENV"
  "$VENV/bin/python" -m pip install --disable-pip-version-check -q --upgrade pip
  "$VENV/bin/python" -m pip install --disable-pip-version-check -q -r "$DIR/backend/requirements.txt"
fi

# --- Ensure a project-local `ffmpeg` next to the venv tools ------------------
# imageio-ffmpeg ships a platform binary (e.g. ffmpeg-linux64-*); symlink it as
# plain `ffmpeg` on PATH so manim finds it without a system install.
if [ ! -e "$VENV/bin/ffmpeg" ]; then
  echo "[setup] Provisioning project-local ffmpeg from imageio-ffmpeg..."
  FFMPEG_SRC="$("$VENV/bin/python" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')"
  ln -sf "$FFMPEG_SRC" "$VENV/bin/ffmpeg"
fi

export PATH="$VENV/bin:$PATH"

# --- LaTeX advisory (MathTex/Tex scenes need it; non-fatal) -----------------
if ! command -v latex >/dev/null 2>&1 && ! command -v xelatex >/dev/null 2>&1; then
  echo "[note] LaTeX not found — math-formula (MathTex/Tex) renders will fall back to"
  echo "       the browser storyboard. Install: macOS 'brew install --cask mactex-no-gui',"
  echo "       Debian/Ubuntu 'sudo apt install texlive-latex-extra texlive-fonts-extra dvisvgm'."
fi

# --- Launch backend (background) + frontend (foreground) --------------------
cleanup() { [ -n "${BACK_PID:-}" ] && kill "$BACK_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

( cd "$DIR/backend" && exec "$VENV/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 ) &
BACK_PID=$!

echo
echo "  Backend  -> http://localhost:8000/docs  (pid $BACK_PID)"
echo "  Frontend -> http://localhost:5173"
echo "  (Ctrl-C stops both)"
echo

cd "$DIR/frontend" && npm run dev
