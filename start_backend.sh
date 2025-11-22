#!/bin/bash
# Start QNWIS Backend Server

echo "🚀 Starting QNWIS Backend..."
echo ""

# Activate virtual environment
source .venv/bin/activate 2>/dev/null || .\.venv\Scripts\Activate.ps1

# Check environment
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  Loading environment from .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Start FastAPI server
echo "Backend starting on http://localhost:8000"
echo "API docs available at http://localhost:8000/docs"
echo ""
python -m qnwis.main
