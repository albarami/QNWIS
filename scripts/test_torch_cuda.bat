@echo off
echo Testing PyTorch CUDA...

REM Clear any CUDA paths that might interfere
set CUDA_HOME=
set CUDA_PATH=

REM Add PyTorch's CUDA DLLs to PATH first
set PATH=d:\lmis_int\.venv\Lib\site-packages\torch\lib;%PATH%

echo Running test...
d:\lmis_int\.venv\Scripts\python.exe -c "import sys; print(f'Python: {sys.version}'); import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"

echo.
echo Exit code: %ERRORLEVEL%
pause
