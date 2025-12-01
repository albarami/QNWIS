@echo off
echo Setting up build environment...

REM Visual Studio environment
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

REM CUDA environment
set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set CUDA_PATH=%CUDA_HOME%
set PATH=%CUDA_HOME%\bin;%PATH%

REM Disable JIT caching issues
set TORCH_CUDA_ARCH_LIST=8.0
set MAX_JOBS=4
set FORCE_CUDA=1

echo.
echo Environment set. CUDA_HOME=%CUDA_HOME%
echo.

echo Uninstalling old exllamav2...
d:\lmis_int\.venv\Scripts\pip.exe uninstall exllamav2 -y

echo.
echo Installing exllamav2 from source with CUDA...
d:\lmis_int\.venv\Scripts\pip.exe install exllamav2 --no-build-isolation --no-cache-dir

echo.
echo Testing import...
d:\lmis_int\.venv\Scripts\python.exe -c "from exllamav2 import ExLlamaV2; print('SUCCESS: ExLlamaV2 imported!')"

echo.
echo Build complete. Exit code: %ERRORLEVEL%

