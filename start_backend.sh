#!/bin/bash
# DocuSentinel AI - Backend Startup Script (Linux/macOS)
# Run from project root: bash start_backend.sh

set -e

echo "======================================="
echo "  DocuSentinel AI - Backend Startup"
echo "======================================="

# Check for .env
if [ ! -f "backend/.env" ]; then
    echo "[WARN] backend/.env not found."
    echo "       Copy .env.example to backend/.env and add your OPENAI_API_KEY."
    echo "       The system will run using local embeddings without an API key."
fi

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install deps
echo "[INFO] Installing backend dependencies..."
pip install -r backend/requirements.txt -q

# Ensure data dirs exist
mkdir -p data/uploads data/vectorstore

echo ""
echo "[INFO] Starting backend on http://localhost:8000"
echo "[INFO] API docs: http://localhost:8000/api/docs"
echo ""

cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
