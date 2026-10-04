#!/bin/bash
# DocuSentinel AI - Frontend Startup Script (Linux/macOS)
# Run from project root: bash start_frontend.sh

set -e

echo "========================================"
echo "  DocuSentinel AI - Frontend Startup"
echo "========================================"

cd frontend

if [ ! -d "node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    npm install
fi

echo ""
echo "[INFO] Starting frontend on http://localhost:5173"
echo ""

npm run dev
