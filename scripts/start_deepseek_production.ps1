# NSIC DeepSeek Production Startup Script
# Run as: .\scripts\start_deepseek_production.ps1
#
# This script:
# 1. Checks GPU availability
# 2. Starts DeepSeek 70B in PRODUCTION mode
# 3. Auto-restarts on crash (up to 5 times)
# 4. Logs everything

$ErrorActionPreference = "Continue"

# Configuration
$MAX_RESTARTS = 5
$RESTART_DELAY_SECONDS = 30
$PORT = 8001
$LOG_DIR = "D:\lmis_int\logs"
$VENV_PATH = "D:\lmis_int\.venv\Scripts\Activate.ps1"

# Create log directory
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force
}

$LOG_FILE = "$LOG_DIR\deepseek_service_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $LOG_FILE -Value $logMessage
}

function Test-DeepSeekHealth {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$PORT/health" -TimeoutSec 10 -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Start-DeepSeekServer {
    Write-Log "Starting DeepSeek 70B Production Server..."
    Write-Log "Port: $PORT"
    Write-Log "GPUs: 2,3,6,7 (320GB total)"
    
    # Activate virtual environment and start server
    $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processStartInfo.FileName = "powershell.exe"
    $processStartInfo.Arguments = "-NoExit -Command `"& '$VENV_PATH'; cd D:\lmis_int; python scripts/deploy_deepseek_native.py --production --port $PORT`""
    $processStartInfo.UseShellExecute = $true
    $processStartInfo.WindowStyle = "Minimized"
    
    $process = [System.Diagnostics.Process]::Start($processStartInfo)
    
    Write-Log "Server process started (PID: $($process.Id))"
    
    # Wait for server to be ready (up to 10 minutes for model loading)
    Write-Log "Waiting for server to load model (this can take 5-10 minutes)..."
    $maxWaitSeconds = 600
    $elapsed = 0
    $checkInterval = 30
    
    while ($elapsed -lt $maxWaitSeconds) {
        Start-Sleep -Seconds $checkInterval
        $elapsed += $checkInterval
        
        if (Test-DeepSeekHealth) {
            Write-Log "SUCCESS: DeepSeek server is READY!" "SUCCESS"
            return $process
        }
        
        # Check if process died
        if ($process.HasExited) {
            Write-Log "ERROR: Server process died during startup" "ERROR"
            return $null
        }
        
        Write-Log "Still loading... ($elapsed/$maxWaitSeconds seconds)"
    }
    
    Write-Log "ERROR: Server failed to become ready within $maxWaitSeconds seconds" "ERROR"
    return $null
}

# Main service loop
Write-Log "=========================================="
Write-Log "NSIC DeepSeek Production Service Starting"
Write-Log "=========================================="
Write-Log "Log file: $LOG_FILE"

# Check Python and CUDA
Write-Log "Checking environment..."
& "$VENV_PATH"
$cudaCheck = python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPUs: {torch.cuda.device_count()}')"
Write-Log "PyTorch: $cudaCheck"

$restartCount = 0
$serverProcess = $null

while ($restartCount -lt $MAX_RESTARTS) {
    # Start or restart server
    if ($null -eq $serverProcess -or $serverProcess.HasExited) {
        if ($restartCount -gt 0) {
            Write-Log "Restart attempt $restartCount/$MAX_RESTARTS..." "WARN"
            Start-Sleep -Seconds $RESTART_DELAY_SECONDS
        }
        
        $serverProcess = Start-DeepSeekServer
        
        if ($null -eq $serverProcess) {
            $restartCount++
            Write-Log "Startup failed, will retry ($restartCount/$MAX_RESTARTS)" "ERROR"
            continue
        }
        
        # Reset restart count on successful start
        $restartCount = 0
    }
    
    # Health monitoring loop
    while (-not $serverProcess.HasExited) {
        Start-Sleep -Seconds 60
        
        if (-not (Test-DeepSeekHealth)) {
            Write-Log "Health check FAILED - server may be unresponsive" "WARN"
            
            # Give it 3 chances
            $failCount = 1
            while ($failCount -lt 3 -and -not (Test-DeepSeekHealth)) {
                Start-Sleep -Seconds 10
                $failCount++
            }
            
            if ($failCount -ge 3) {
                Write-Log "Server unresponsive after 3 health checks - restarting" "ERROR"
                try {
                    $serverProcess.Kill()
                } catch {}
                $restartCount++
                break
            }
        }
    }
    
    if ($serverProcess.HasExited) {
        Write-Log "Server process exited (code: $($serverProcess.ExitCode))" "ERROR"
        $restartCount++
    }
}

Write-Log "=========================================="
Write-Log "CRITICAL: Max restarts exceeded ($MAX_RESTARTS)" "CRITICAL"
Write-Log "MANUAL INTERVENTION REQUIRED"
Write-Log "=========================================="

# Keep window open
Read-Host "Press Enter to exit"

