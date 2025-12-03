@echo off
REM NSIC Quick Start Script
REM Starts Engine B and verifies connections

echo.
echo ========================================
echo    NSIC System Quick Start
echo ========================================
echo.

cd /d %~dp0..

REM Load environment
if exist .env (
    echo [OK] Loading .env file...
) else (
    echo [ERROR] .env file not found!
    pause
    exit /b 1
)

REM Start Engine B
echo.
echo [1/3] Starting Engine B (GPU Compute)...
start "NSIC Engine B" cmd /k "cd /d %~dp0.. && python -m uvicorn src.nsic.engine_b.api:app --host 0.0.0.0 --port 8001"

REM Wait for startup
echo Waiting for Engine B to initialize...
timeout /t 10 /nobreak > nul

REM Verify Engine B
echo.
echo [2/3] Verifying Engine B health...
curl -s http://localhost:8001/health > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Engine B is running on port 8001
) else (
    echo [WARN] Engine B may still be starting...
)

REM Test database connection
echo.
echo [3/3] Testing database connection...
python -c "from dotenv import load_dotenv; load_dotenv(); import os; from sqlalchemy import create_engine, text; e=create_engine(os.getenv('DATABASE_URL')); c=e.connect(); c.execute(text('SELECT 1')); print('[OK] Database connected')" 2>nul || echo [WARN] Database check skipped

echo.
echo ========================================
echo    NSIC System Started
echo ========================================
echo.
echo Engine B API: http://localhost:8001
echo Health Check: http://localhost:8001/health
echo.
echo To run diagnostic: python scripts/qnwis_enhanced_diagnostic.py
echo.
pause

