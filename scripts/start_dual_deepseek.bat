@echo off
REM NSIC Dual DeepSeek Startup - CORRECT GPU Allocation
REM
REM This starts BOTH DeepSeek instances:
REM   Instance 1: GPUs 2-3, Port 8001, Scenarios 1-12
REM   Instance 2: GPUs 6-7, Port 8002, Scenarios 13-24

echo ============================================================
echo NSIC Dual DeepSeek Deployment
echo ============================================================
echo.
echo CORRECT GPU Allocation:
echo   GPU 0-1: Embeddings (instructor-xl)
echo   GPU 2-3: DeepSeek Instance 1 (port 8001)
echo   GPU 4:   Knowledge Graph
echo   GPU 5:   Deep Verification
echo   GPU 6-7: DeepSeek Instance 2 (port 8002)
echo.

cd /d D:\lmis_int
call .venv\Scripts\activate.bat

echo.
echo [%date% %time%] Killing any existing DeepSeek processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *DeepSeek*" 2>nul

echo.
echo [%date% %time%] Starting Instance 1 (GPUs 2-3, Port 8001)...
start "DeepSeek Instance 1" cmd /c "call .venv\Scripts\activate.bat && python scripts/deploy_deepseek_correct.py --instance 1"

echo Waiting 30 seconds before starting Instance 2...
timeout /t 30 /nobreak

echo.
echo [%date% %time%] Starting Instance 2 (GPUs 6-7, Port 8002)...
start "DeepSeek Instance 2" cmd /c "call .venv\Scripts\activate.bat && python scripts/deploy_deepseek_correct.py --instance 2"

echo.
echo ============================================================
echo Both instances starting. Model loading takes 5-10 minutes.
echo.
echo Check health:
echo   curl http://localhost:8001/health
echo   curl http://localhost:8002/health
echo ============================================================

pause

