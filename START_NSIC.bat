@echo off
title NSIC System Startup
echo.
echo ============================================================
echo           NSIC SYSTEM STARTUP
echo ============================================================
echo.

cd /d D:\lmis_int

echo Starting all services...
python scripts/start_all_services.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Some services failed to start!
    echo Please check the output above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo           SYSTEM READY!
echo ============================================================
echo.
pause

