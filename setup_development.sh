#!/bin/bash
# QNWIS Development Environment Setup
# Automated deployment script for Week 3 validated system

echo "================================================================================"
echo "QNWIS DEVELOPMENT DEPLOYMENT - Week 3 Production-Ready System"
echo "================================================================================"
echo ""

# Check prerequisites
echo "Step 1: Checking prerequisites..."
python --version || { echo "❌ Python not found"; exit 1; }
node --version || { echo "❌ Node.js not found"; exit 1; }
psql --version || { echo "❌ PostgreSQL not found"; exit 1; }
echo "✅ All prerequisites present"
echo ""

# Backend setup
echo "Step 2: Setting up backend..."
cd "$(dirname "$0")"

# Check .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Copy from .env.example and configure."
    exit 1
fi

# Verify critical API keys
source .env
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set in .env"
    exit 1
fi
echo "✅ Environment variables configured"
echo ""

# Create virtual environment if needed
if [ ! -d .venv ]; then
    echo "Creating Python virtual environment..."
    python -m venv .venv
fi

# Activate and install
echo "Installing Python dependencies..."
source .venv/bin/activate 2>/dev/null || .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
echo "✅ Backend dependencies installed"
echo ""

# Database setup
echo "Step 3: Setting up database..."
python scripts/init_db.py
python scripts/load_wb_cache.py
echo "✅ Database initialized with 128 cached indicators"
echo ""

# Validation
echo "Step 4: Running validation tests..."
python validate_langgraph_refactor.py
echo "✅ Validation complete"
echo ""

# Frontend setup
echo "Step 5: Setting up frontend..."
cd qnwis-frontend

if [ ! -d node_modules ]; then
    echo "Installing frontend dependencies..."
    npm install
    echo "✅ Frontend dependencies installed"
else
    echo "✅ Frontend dependencies already installed"
fi
cd ..
echo ""

echo "================================================================================"
echo "✅ DEVELOPMENT ENVIRONMENT READY"
echo "================================================================================"
echo ""
echo "To start the system:"
echo ""
echo "Terminal 1 (Backend):"
echo "  cd $(pwd)"
echo "  source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows"
echo "  python -m qnwis.main"
echo "  → Backend will be available at http://localhost:8000"
echo ""
echo "Terminal 2 (Frontend):"
echo "  cd $(pwd)/qnwis-frontend"
echo "  npm run dev"
echo "  → Frontend will be available at http://localhost:3000"
echo ""
echo "Access the system at: http://localhost:3000"
echo "API documentation at: http://localhost:8000/docs"
echo ""
