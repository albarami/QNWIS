@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set PATH=%CUDA_HOME%\bin;%PATH%
set TORCH_CUDA_ARCH_LIST=8.0

echo Running ExLlamaV2 build test...
d:\lmis_int\.venv\Scripts\python.exe D:\lmis_int\scripts\test_torch_first.py 2>&1

echo.
echo Exit code: %ERRORLEVEL%

