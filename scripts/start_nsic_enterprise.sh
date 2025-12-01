#!/bin/bash
# start_nsic_enterprise.sh - Enterprise Grade NSIC Startup Script
# 
# Starts all persistent GPU services:
# - Embeddings Server (GPU 0-1, Port 8003)
# - Knowledge Graph Server (GPU 4, Port 8004)
# - Verification Server (GPU 5, Port 8005)
# - DeepSeek Instance 1 (GPU 2-3, Port 8001)
# - DeepSeek Instance 2 (GPU 6-7, Port 8002)
#
# All models are loaded at startup and kept in GPU memory permanently.

set -e

echo "============================================================"
echo "  NSIC ENTERPRISE STARTUP - Persistent GPU Services"
echo "============================================================"
echo ""

# Configuration
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate virtual environment
source .venv/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null || true

# Function to check if a port is in use
check_port() {
    nc -z localhost "$1" 2>/dev/null
}

# Function to wait for a service
wait_for_service() {
    local port=$1
    local name=$2
    local max_wait=${3:-120}
    local elapsed=0
    
    echo "  Waiting for $name (port $port)..."
    while ! check_port "$port"; do
        sleep 5
        elapsed=$((elapsed + 5))
        if [ $elapsed -ge $max_wait ]; then
            echo "  TIMEOUT: $name did not start within ${max_wait}s"
            return 1
        fi
        echo "    ... waiting ($elapsed s)"
    done
    echo "  $name is ready!"
    return 0
}

# ============================================================================
# 1. Start Embeddings Server (GPU 0-1, Port 8003)
# ============================================================================
echo ""
echo "[1/5] EMBEDDINGS SERVER (GPU 0-1, Port 8003)"

if check_port 8003; then
    echo "  Already running on port 8003"
else
    echo "  Starting embeddings server..."
    CUDA_VISIBLE_DEVICES=0,1 python -m src.nsic.servers.embeddings_server --port 8003 &
    sleep 5
fi

# ============================================================================
# 2. Start Knowledge Graph Server (GPU 4, Port 8004)
# ============================================================================
echo ""
echo "[2/5] KNOWLEDGE GRAPH SERVER (GPU 4, Port 8004)"

if check_port 8004; then
    echo "  Already running on port 8004"
else
    echo "  Starting KG server..."
    CUDA_VISIBLE_DEVICES=4 python -m src.nsic.servers.kg_server --port 8004 &
    sleep 5
fi

# ============================================================================
# 3. Start Verification Server (GPU 5, Port 8005)
# ============================================================================
echo ""
echo "[3/5] VERIFICATION SERVER (GPU 5, Port 8005)"

if check_port 8005; then
    echo "  Already running on port 8005"
else
    echo "  Starting verification server..."
    CUDA_VISIBLE_DEVICES=5 python -m src.nsic.servers.verification_server --port 8005 &
    sleep 5
fi

# ============================================================================
# 4. Start DeepSeek Instance 1 (GPU 2-3, Port 8001)
# ============================================================================
echo ""
echo "[4/5] DEEPSEEK INSTANCE 1 (GPU 2-3, Port 8001)"

if check_port 8001; then
    echo "  Already running on port 8001"
else
    echo "  Starting DeepSeek Instance 1..."
    CUDA_VISIBLE_DEVICES=2,3 python -m vllm.entrypoints.openai.api_server \
        --model deepseek-ai/DeepSeek-R1-Distill-Llama-70B \
        --tensor-parallel-size 2 --port 8001 \
        --gpu-memory-utilization 0.85 --swap-space 16 &
    sleep 5
fi

# ============================================================================
# 5. Start DeepSeek Instance 2 (GPU 6-7, Port 8002)
# ============================================================================
echo ""
echo "[5/5] DEEPSEEK INSTANCE 2 (GPU 6-7, Port 8002)"

if check_port 8002; then
    echo "  Already running on port 8002"
else
    echo "  Starting DeepSeek Instance 2..."
    CUDA_VISIBLE_DEVICES=6,7 python -m vllm.entrypoints.openai.api_server \
        --model deepseek-ai/DeepSeek-R1-Distill-Llama-70B \
        --tensor-parallel-size 2 --port 8002 \
        --gpu-memory-utilization 0.85 --swap-space 16 &
    sleep 5
fi

# ============================================================================
# Wait for services
# ============================================================================
echo ""
echo "============================================================"
echo "  Waiting for services to initialize..."
echo "============================================================"

wait_for_service 8003 "Embeddings" 180
wait_for_service 8004 "Knowledge Graph" 180
wait_for_service 8005 "Verification" 180
wait_for_service 8001 "DeepSeek 1" 300
wait_for_service 8002 "DeepSeek 2" 300

# ============================================================================
# Health Checks
# ============================================================================
echo ""
echo "============================================================"
echo "  Running Health Checks..."
echo "============================================================"

echo ""
echo "Embeddings Server:"
curl -s http://localhost:8003/health | python -m json.tool 2>/dev/null || echo "  FAILED"

echo ""
echo "Knowledge Graph Server:"
curl -s http://localhost:8004/health | python -m json.tool 2>/dev/null || echo "  FAILED"

echo ""
echo "Verification Server:"
curl -s http://localhost:8005/health | python -m json.tool 2>/dev/null || echo "  FAILED"

echo ""
echo "DeepSeek Instance 1:"
curl -s http://localhost:8001/v1/models | python -m json.tool 2>/dev/null || echo "  FAILED"

echo ""
echo "DeepSeek Instance 2:"
curl -s http://localhost:8002/v1/models | python -m json.tool 2>/dev/null || echo "  FAILED"

# ============================================================================
# GPU Memory Status
# ============================================================================
echo ""
echo "============================================================"
echo "  GPU Memory Status (should show memory on ALL GPUs)"
echo "============================================================"

nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv

# ============================================================================
# Final Status
# ============================================================================
echo ""
echo "============================================================"
echo "  ALL SERVICES STARTED - Enterprise Grade Ready!"
echo "============================================================"
echo ""
echo "Service URLs:"
echo "  Embeddings:      http://localhost:8003"
echo "  Knowledge Graph: http://localhost:8004"
echo "  Verification:    http://localhost:8005"
echo "  DeepSeek 1:      http://localhost:8001"
echo "  DeepSeek 2:      http://localhost:8002"
echo ""

