@echo off
REM Quick Start Script for QNWIS System
REM This script starts all required services

echo ========================================
echo QNWIS Multi-Agent System - Quick Start
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure it.
    echo.
    pause
    exit /b 1
)

echo [1/4] Checking dependencies...
python -c "import chainlit, fastapi, langgraph" 2>nul
if errorlevel 1 (
    echo [ERROR] Missing dependencies. Run: pip install -r requirements.txt
    pause
    exit /b 1
)
echo     ✓ Dependencies OK

echo.
echo [2/4] Checking Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo     ⚠ Redis not running. Starting with Docker...
    docker run -d --name qnwis-redis -p 6379:6379 redis:latest >nul 2>&1
    timeout /t 2 >nul
    redis-cli ping >nul 2>&1
    if errorlevel 1 (
        echo     [WARNING] Could not start Redis. Some features may not work.
    ) else (
        echo     ✓ Redis started
    )
) else (
    echo     ✓ Redis OK
)

echo.
echo [3/4] Starting API Server...
start "QNWIS API Server" cmd /k "python -m uvicorn src.qnwis.api.server:app --host 127.0.0.1 --port 8000"
timeout /t 3 >nul
echo     ✓ API Server started on http://localhost:8000

echo.
echo [4/4] Starting Chainlit UI...
start "QNWIS Chainlit UI" cmd /k "python -m chainlit run src/qnwis/ui/chainlit_app_llm.py --port 8002"
timeout /t 3 >nul
echo     ✓ Chainlit UI started on http://localhost:8002

echo.
echo ========================================
echo System Started Successfully!
echo ========================================
echo.
echo Services:
echo   - API Server:    http://localhost:8000
echo   - Chainlit UI:   http://localhost:8002
echo   - API Health:    http://localhost:8000/health
echo.
echo Press Ctrl+C in each window to stop services.
echo.
pause
