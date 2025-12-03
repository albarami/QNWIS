<#
.SYNOPSIS
    NSIC System Startup Script - Launches all services and verifies connections

.DESCRIPTION
    This script starts the complete NSIC (National Strategic Intelligence Center) system:
    - PostgreSQL database verification
    - Engine B (GPU compute services: Monte Carlo, Forecasting, Sensitivity, etc.)
    - RAG document store and embeddings
    - Knowledge Graph
    - Frontend application
    - Health checks and connection verification

.EXAMPLE
    .\scripts\start_nsic_system.ps1
    .\scripts\start_nsic_system.ps1 -SkipFrontend
    .\scripts\start_nsic_system.ps1 -DiagnosticAfterStart

.NOTES
    Author: NSIC Team
    Version: 1.0.0
#>

param(
    [switch]$SkipFrontend,
    [switch]$DiagnosticAfterStart,
    [switch]$Verbose
)

# ============================================================
# CONFIGURATION
# ============================================================
$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

# Service ports
$Config = @{
    EngineB_Port = 8001
    Frontend_Port = 3000
    API_Port = 8000
    PostgreSQL_Port = 5432
    Embedding_Model = "all-mpnet-base-v2"
}

# Colors for output
function Write-Status { param($Message) Write-Host "[STATUS] $Message" -ForegroundColor Cyan }
function Write-Success { param($Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-Header { param($Message) 
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Blue
    Write-Host " $Message" -ForegroundColor Blue
    Write-Host ("=" * 60) -ForegroundColor Blue
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Test-PortInUse {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -ne $connection
}

function Wait-ForService {
    param(
        [string]$Name,
        [string]$Url,
        [int]$TimeoutSeconds = 60,
        [int]$IntervalSeconds = 2
    )
    
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {
            # Service not ready yet
        }
        Start-Sleep -Seconds $IntervalSeconds
        $elapsed += $IntervalSeconds
        Write-Host "." -NoNewline
    }
    Write-Host ""
    return $false
}

function Stop-ServiceOnPort {
    param([int]$Port)
    
    $processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
                 Select-Object -ExpandProperty OwningProcess -Unique
    
    foreach ($pid in $processes) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Warning "Stopping existing process on port $Port (PID: $pid, Name: $($proc.ProcessName))"
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}

# ============================================================
# MAIN STARTUP SEQUENCE
# ============================================================

Write-Host ""
Write-Host "    _   _______  _____ ______" -ForegroundColor Cyan
Write-Host "   / | / / ___/ /  _/ / ____/" -ForegroundColor Cyan
Write-Host "  /  |/ /\__ \  / /  / /     " -ForegroundColor Cyan
Write-Host " / /|  /___/ /_/ /  / /___   " -ForegroundColor Cyan
Write-Host "/_/ |_//____//___/  \____/   " -ForegroundColor Cyan
Write-Host ""
Write-Host "National Strategic Intelligence Center - System Startup" -ForegroundColor White
Write-Host ("=" * 60) -ForegroundColor DarkGray
Write-Host ""

$StartTime = Get-Date

# ============================================================
# STEP 1: ENVIRONMENT SETUP
# ============================================================
Write-Header "STEP 1: Environment Setup"

# Load .env file
if (Test-Path ".env") {
    Write-Status "Loading environment variables from .env..."
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
    Write-Success "Environment variables loaded"
} else {
    Write-Error ".env file not found! Copy .env.example to .env and configure"
    exit 1
}

# Verify Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Success "Python found: $pythonVersion"
} else {
    Write-Error "Python not found in PATH"
    exit 1
}

# ============================================================
# STEP 2: DATABASE VERIFICATION
# ============================================================
Write-Header "STEP 2: PostgreSQL Database"

$dbUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
if ($dbUrl) {
    Write-Status "Checking PostgreSQL connection..."
    
    try {
        $result = python -c "
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('OK')
" 2>&1
        
        if ($result -match "OK") {
            Write-Success "PostgreSQL connected successfully"
        } else {
            Write-Warning "PostgreSQL connection issue: $result"
        }
    } catch {
        Write-Warning "Could not verify PostgreSQL: $_"
    }
} else {
    Write-Warning "DATABASE_URL not set - database features may not work"
}

# ============================================================
# STEP 3: ENGINE B (GPU COMPUTE SERVICES)
# ============================================================
Write-Header "STEP 3: Engine B (GPU Compute Services)"

if (Test-PortInUse -Port $Config.EngineB_Port) {
    Write-Status "Engine B already running on port $($Config.EngineB_Port)"
    
    # Verify it's healthy
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:$($Config.EngineB_Port)/health" -Method GET -TimeoutSec 5
        Write-Success "Engine B healthy - Services: Monte Carlo, Forecasting, Sensitivity, Thresholds, Benchmarking"
    } catch {
        Write-Warning "Engine B running but health check failed - restarting..."
        Stop-ServiceOnPort -Port $Config.EngineB_Port
        Start-Sleep -Seconds 2
    }
}

if (-not (Test-PortInUse -Port $Config.EngineB_Port)) {
    Write-Status "Starting Engine B on port $($Config.EngineB_Port)..."
    
    $engineBJob = Start-Job -ScriptBlock {
        param($root)
        Set-Location $root
        python -m uvicorn src.nsic.engine_b.api:app --host 0.0.0.0 --port 8001
    } -ArgumentList $ProjectRoot
    
    Write-Status "Waiting for Engine B to be ready"
    $ready = Wait-ForService -Name "Engine B" -Url "http://localhost:$($Config.EngineB_Port)/health" -TimeoutSeconds 30
    
    if ($ready) {
        Write-Success "Engine B started successfully"
        
        # Check GPU availability
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:$($Config.EngineB_Port)/health" -Method GET
            $gpuServices = @("monte_carlo", "forecasting", "sensitivity", "thresholds", "benchmark", "correlation", "optimization")
            $gpuCount = 0
            foreach ($svc in $gpuServices) {
                if ($health.$svc.gpu_available) { $gpuCount++ }
            }
            Write-Success "  GPU Services: $gpuCount/$($gpuServices.Count) with GPU acceleration"
        } catch {
            Write-Warning "  Could not check GPU status"
        }
    } else {
        Write-Error "Engine B failed to start within timeout"
    }
}

# ============================================================
# STEP 4: RAG & EMBEDDINGS
# ============================================================
Write-Header "STEP 4: RAG System & Embeddings"

Write-Status "Initializing RAG document store and embeddings..."

$ragResult = python -c "
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

try:
    from src.qnwis.rag.retriever import DocumentStore, SentenceEmbedder
    from src.qnwis.rag.document_loader import load_source_documents
    
    # Initialize embedder
    embedder = SentenceEmbedder()
    print(f'EMBEDDER_OK: {embedder.model_name}')
    
    # Initialize document store
    store = DocumentStore(embedder=embedder)
    
    # Load documents
    docs = load_source_documents()
    print(f'DOCUMENTS_OK: {len(docs)}')
    
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1

if ($ragResult -match "EMBEDDER_OK: (.+)") {
    Write-Success "Embeddings model loaded: $($Matches[1])"
}

if ($ragResult -match "DOCUMENTS_OK: (\d+)") {
    Write-Success "RAG documents available: $($Matches[1]) documents"
} elseif ($ragResult -match "ERROR: (.+)") {
    Write-Warning "RAG initialization warning: $($Matches[1])"
}

# ============================================================
# STEP 5: KNOWLEDGE GRAPH
# ============================================================
Write-Header "STEP 5: Knowledge Graph"

Write-Status "Loading Knowledge Graph..."

$kgResult = python -c "
import sys
sys.path.insert(0, '.')
from pathlib import Path

try:
    from src.qnwis.knowledge.graph_builder import QNWISKnowledgeGraph
    
    kg = QNWISKnowledgeGraph()
    kg_path = Path('data/knowledge_graph.json')
    
    if kg_path.exists():
        kg.load(kg_path)
        print(f'KG_OK: {len(kg.graph.nodes)} nodes, {len(kg.graph.edges)} edges')
    else:
        print('KG_MISSING: Knowledge graph file not found')
        
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1

if ($kgResult -match "KG_OK: (.+)") {
    Write-Success "Knowledge Graph loaded: $($Matches[1])"
} elseif ($kgResult -match "KG_MISSING") {
    Write-Warning "Knowledge Graph file not found - will use defaults"
} else {
    Write-Warning "Knowledge Graph: $kgResult"
}

# ============================================================
# STEP 6: DETERMINISTIC AGENTS VERIFICATION
# ============================================================
Write-Header "STEP 6: Deterministic Agents"

Write-Status "Verifying deterministic agent data access..."

$agentResult = python -c "
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

try:
    from src.qnwis.agents.base import DataClient
    from src.qnwis.data.deterministic.registry import QueryRegistry
    
    # Load registry
    registry = QueryRegistry()
    registry.load_all()
    query_count = len(registry.list_query_ids())
    print(f'QUERIES_OK: {query_count}')
    
    # Test DataClient
    client = DataClient()
    result = client.run('syn_unemployment_gcc_latest')
    rows = list(result.rows) if result.rows else []
    print(f'DATACLIENT_OK: {len(rows)} rows')
    
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1

if ($agentResult -match "QUERIES_OK: (\d+)") {
    Write-Success "Query Registry: $($Matches[1]) queries registered"
}

if ($agentResult -match "DATACLIENT_OK: (\d+)") {
    Write-Success "DataClient verified: $($Matches[1]) test rows retrieved"
} elseif ($agentResult -match "ERROR: (.+)") {
    Write-Warning "Agent verification warning: $($Matches[1])"
}

# ============================================================
# STEP 7: FRONTEND (Optional)
# ============================================================
if (-not $SkipFrontend) {
    Write-Header "STEP 7: Frontend Application"
    
    $frontendPath = Join-Path $ProjectRoot "frontend"
    
    if (Test-Path $frontendPath) {
        if (Test-PortInUse -Port $Config.Frontend_Port) {
            Write-Status "Frontend already running on port $($Config.Frontend_Port)"
        } else {
            Write-Status "Starting frontend on port $($Config.Frontend_Port)..."
            
            $frontendJob = Start-Job -ScriptBlock {
                param($path)
                Set-Location $path
                npm run dev
            } -ArgumentList $frontendPath
            
            Write-Status "Waiting for frontend to be ready"
            $ready = Wait-ForService -Name "Frontend" -Url "http://localhost:$($Config.Frontend_Port)" -TimeoutSeconds 60
            
            if ($ready) {
                Write-Success "Frontend started at http://localhost:$($Config.Frontend_Port)"
            } else {
                Write-Warning "Frontend may not be fully ready - check manually"
            }
        }
    } else {
        Write-Warning "Frontend directory not found at $frontendPath"
    }
} else {
    Write-Status "Skipping frontend startup (--SkipFrontend flag)"
}

# ============================================================
# STEP 8: FINAL HEALTH CHECK
# ============================================================
Write-Header "STEP 8: Final System Health Check"

$healthChecks = @{
    "Engine B API" = "http://localhost:$($Config.EngineB_Port)/health"
}

if (-not $SkipFrontend) {
    $healthChecks["Frontend"] = "http://localhost:$($Config.Frontend_Port)"
}

$allHealthy = $true
foreach ($service in $healthChecks.Keys) {
    try {
        $response = Invoke-WebRequest -Uri $healthChecks[$service] -Method GET -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "$service : HEALTHY"
        } else {
            Write-Warning "$service : Status $($response.StatusCode)"
            $allHealthy = $false
        }
    } catch {
        Write-Error "$service : NOT RESPONDING"
        $allHealthy = $false
    }
}

# ============================================================
# SUMMARY
# ============================================================
$EndTime = Get-Date
$Duration = $EndTime - $StartTime

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Blue
Write-Host " NSIC SYSTEM STARTUP COMPLETE" -ForegroundColor Blue
Write-Host ("=" * 60) -ForegroundColor Blue
Write-Host ""
Write-Host "  Startup Duration: $($Duration.TotalSeconds.ToString('F1')) seconds" -ForegroundColor White
Write-Host ""

if ($allHealthy) {
    Write-Host "  [ALL SYSTEMS OPERATIONAL]" -ForegroundColor Green
} else {
    Write-Host "  [SOME SERVICES MAY NEED ATTENTION]" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Service URLs:" -ForegroundColor White
Write-Host "    Engine B API:  http://localhost:$($Config.EngineB_Port)" -ForegroundColor Gray
Write-Host "    Engine B Health: http://localhost:$($Config.EngineB_Port)/health" -ForegroundColor Gray
if (-not $SkipFrontend) {
    Write-Host "    Frontend:      http://localhost:$($Config.Frontend_Port)" -ForegroundColor Gray
}
Write-Host ""

# ============================================================
# OPTIONAL: RUN DIAGNOSTIC
# ============================================================
if ($DiagnosticAfterStart) {
    Write-Header "Running System Diagnostic"
    Write-Status "Starting diagnostic check..."
    
    python scripts/qnwis_enhanced_diagnostic.py --query qatarization --quick
}

Write-Host ""
Write-Host "To run a diagnostic: python scripts/qnwis_enhanced_diagnostic.py" -ForegroundColor DarkGray
Write-Host "To stop all services: Get-Process python | Stop-Process -Force" -ForegroundColor DarkGray
Write-Host ""

