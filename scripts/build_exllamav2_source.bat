@echo off
echo ============================================
echo Building ExLlamaV2 from source with CUDA
echo ============================================

REM Visual Studio environment
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

REM CUDA environment  
set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set CUDA_PATH=%CUDA_HOME%
set CUDA_ROOT=%CUDA_HOME%
set PATH=%CUDA_HOME%\bin;%CUDA_HOME%\libnvvp;%PATH%

REM Build settings - A100 GPU architecture
set TORCH_CUDA_ARCH_LIST=8.0
set MAX_JOBS=4
set FORCE_CUDA=1

REM Python environment
set PYTHONPATH=d:\lmis_int\.venv\Lib\site-packages
set PIP_NO_BUILD_ISOLATION=0

echo.
echo Environment:
echo   CUDA_HOME=%CUDA_HOME%
echo   TORCH_CUDA_ARCH_LIST=%TORCH_CUDA_ARCH_LIST%
echo   Python: d:\lmis_int\.venv\Scripts\python.exe
echo.

REM Clone and build
echo Cloning ExLlamaV2 repository...
cd /d D:\
if exist exllamav2_build rmdir /s /q exllamav2_build
mkdir exllamav2_build
cd exllamav2_build

git clone --depth 1 https://github.com/turboderp/exllamav2.git .
if %ERRORLEVEL% neq 0 (
    echo ERROR: Git clone failed
    exit /b 1
)

echo.
echo Building with CUDA...
d:\lmis_int\.venv\Scripts\pip.exe install . --no-build-isolation -v

echo.
echo Build exit code: %ERRORLEVEL%

echo.
echo Testing import...
d:\lmis_int\.venv\Scripts\python.exe -c "print('Testing exllamav2 import...'); from exllamav2 import ExLlamaV2; print('SUCCESS!')"

echo.
echo Final exit code: %ERRORLEVEL%

