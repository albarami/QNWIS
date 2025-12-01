@echo off
REM NSIC DeepSeek 70B Production Startup
REM Always runs 70B at full FP16 quality - NO COMPROMISES
REM 
REM Usage: Run this batch file to start DeepSeek

echo ==========================================
echo NSIC DeepSeek 70B Production Server
echo ==========================================
echo.
echo Model: DeepSeek-R1-Distill-Llama-70B
echo Precision: Full FP16 (NO quantization)
echo GPUs: 2,3,6,7 (320GB VRAM)
echo Port: 8001
echo.

cd /d D:\lmis_int
call .venv\Scripts\activate.bat

:START
echo [%date% %time%] Starting DeepSeek 70B...
python scripts/deploy_deepseek_native.py --production --port 8001

echo.
echo [%date% %time%] Server stopped. Restarting in 30 seconds...
echo Press Ctrl+C to exit
timeout /t 30
goto START

