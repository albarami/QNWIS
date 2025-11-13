@echo off
setlocal enableextensions

echo ========================================
echo QNWIS Full System Launch (Dev)
echo ========================================
echo.

REM Ensure child Python processes can import qnwis.*
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

REM Provider selection
if not defined ANTHROPIC_API_KEY (
  echo Using STUB provider (no ANTHROPIC_API_KEY set)
  set "QNWIS_LLM_PROVIDER=stub"
  set "QNWIS_STUB_TOKEN_DELAY_MS=25"
) else (
  echo Using Anthropic Claude (real LLM)
  set "QNWIS_LLM_PROVIDER=anthropic"
  set "QNWIS_ANTHROPIC_MODEL=claude-sonnet-4-5-20250929"
)

set "QNWIS_LLM_TIMEOUT=60"
set "QNWIS_LLM_MAX_RETRIES=3"

echo.
echo Configuration:
echo   Provider: %QNWIS_LLM_PROVIDER%
echo   Timeout: %QNWIS_LLM_TIMEOUT%s
echo.

REM Keep ports aligned with UI expectation (8050)
python "%~dp0launch_full_system.py" --provider %QNWIS_LLM_PROVIDER% --ui-port 8050

pause
