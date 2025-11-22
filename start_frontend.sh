#!/bin/bash
# Start QNWIS Frontend Server

echo "🚀 Starting QNWIS Frontend..."
echo ""

cd qnwis-frontend

echo "Frontend starting on http://localhost:3000"
echo "Connecting to backend at http://localhost:8000"
echo ""

npm run dev
