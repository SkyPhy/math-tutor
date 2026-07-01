@echo off
REM Start math-tutor backend (FastAPI :8000) and frontend (Vite :5173)
REM Runnable from cmd or PowerShell: just run  start.bat
REM
REM Backend runs from a PROJECT-LOCAL venv (backend\.venv) that bundles Manim CE
REM + ffmpeg, so /manim/render produces real MP4s. The venv\Scripts dir is put on
REM PATH ahead of the process so manim_render.available() (shutil.which) finds both.
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "VENV=%~dp0backend\.venv"

REM --- Bootstrap venv on first run (or if it went missing) -------------------
if not exist "%VENV%\Scripts\python.exe" (
  echo [setup] Creating backend venv + installing deps ^(first run, may take a few minutes^)...
  py -3.12 -m venv "%VENV%"
  "%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
  "%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r "%~dp0backend\requirements.txt"
)

REM --- Ensure a project-local ffmpeg.exe next to manim.exe ------------------
if not exist "%VENV%\Scripts\ffmpeg.exe" (
  echo [setup] Provisioning project-local ffmpeg.exe from imageio-ffmpeg...
  "%VENV%\Scripts\python.exe" -c "import shutil, imageio_ffmpeg, os; shutil.copyfile(imageio_ffmpeg.get_ffmpeg_exe(), os.path.join(r'%VENV%','Scripts','ffmpeg.exe'))"
)

REM --- Launch: prepend venv\Scripts so manim + ffmpeg are on PATH ------------
start "math-tutor-backend"  cmd /k "cd /d "%~dp0backend" && set "PATH=%VENV%\Scripts;%PATH%" && "%VENV%\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
start "math-tutor-frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo   Backend  -^> http://localhost:8000/docs
echo   Frontend -^> http://localhost:5173
echo   (each runs in its own window; close them or run stop.bat to stop)
