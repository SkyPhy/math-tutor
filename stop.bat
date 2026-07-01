@echo off
REM Stop math-tutor backend (:8000) and frontend (:5173) by killing their listeners
REM Runnable from cmd or PowerShell: just run  stop.bat

for %%p in (8000 5173) do (
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p " ^| findstr LISTENING') do (
    taskkill /PID %%a /F /T >nul 2>&1
  )
)

echo Stopped backend (:8000) and frontend (:5173).
