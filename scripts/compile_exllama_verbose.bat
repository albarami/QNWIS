@echo off
echo Setting up environment for ExLlamaV2 compilation...

REM Visual Studio environment
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

REM CUDA environment
set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set PATH=%CUDA_HOME%\bin;%PATH%

REM Set PyTorch environment
set TORCH_CUDA_ARCH_LIST=8.0

echo.
echo Compiling ExLlamaV2 with verbose output...
echo This may take 5-10 minutes...
echo.

d:\lmis_int\.venv\Scripts\python.exe -c "import os; os.environ['TORCH_CUDA_ARCH_LIST']='8.0'; import exllamav2.ext as ext; ext.verbose=True; ext.make_c_ext()"

echo.
echo Exit code: %ERRORLEVEL%

