@echo off
echo ============================================================
echo  QNWIS System Restart
echo ============================================================
echo.

echo Step 1: Stopping existing servers...
echo.

REM Find and kill API server on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo   Killing API server (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

REM Find and kill Chainlit on port 8001
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    echo   Killing Chainlit server (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

echo   Done!
echo.

echo Step 2: Starting API server (port 8000)...
echo.
start "QNWIS API Server" cmd /k "uvicorn src.qnwis.api.server:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 >nul

echo Step 3: Starting Chainlit UI (port 8001)...
echo.
start "QNWIS Chainlit UI" cmd /k "chainlit run src/qnwis/ui/chainlit_app_llm.py --port 8001"

timeout /t 3 >nul

echo.
echo ============================================================
echo  System Started!
echo ============================================================
echo.
echo   API Server:      http://localhost:8000
echo   Chainlit UI:     http://localhost:8001
echo   API Docs:        http://localhost:8000/docs
echo.
echo Press any key to open Chainlit UI in browser...
pause >nul

start http://localhost:8001

echo.
echo Done! The UI should open in your browser.
echo.
