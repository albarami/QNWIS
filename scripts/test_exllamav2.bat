@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set PATH=%CUDA_HOME%\bin;%PATH%

echo.
echo Testing ExLlamaV2 with CUDA...
echo.

d:\lmis_int\.venv\Scripts\python.exe -c "from exllamav2 import ExLlamaV2, ExLlamaV2Config; import torch; print('ExLlamaV2 loaded successfully!'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"

echo.
echo Test complete. Exit code: %ERRORLEVEL%
