@echo off
echo [SIGMA AGENT] ---------------------------------------------
echo [SIGMA AGENT] STEP 1: Killing old processes (Port cleanup)...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1
echo [SIGMA AGENT] Cleanup complete.
echo [SIGMA AGENT] ---------------------------------------------

echo [SIGMA AGENT] STEP 2: Starting Backend (Wait 8 seconds)...
start "SIGMA BACKEND" cmd /k "cd python-core && .venv\Scripts\activate && python -m app.main || (echo. && echo [ERROR] BACKEND CRASHED! Check logs above. && echo. && pause)"

echo [SIGMA AGENT] Waiting for Backend to initialize...
timeout /t 8 >nul

echo [SIGMA AGENT] ---------------------------------------------
echo [SIGMA AGENT] STEP 3: Starting Frontend...
start "SIGMA FRONTEND" cmd /k "npm run dev"

echo [SIGMA AGENT] ---------------------------------------------
echo [SIGMA AGENT] SYSTEM RESTARTED SUCCESSFULLY!
echo [SIGMA AGENT] You can close this launcher window now.
pause
