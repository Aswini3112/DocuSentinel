# DocuSentinel AI - Backend Startup Script (Windows PowerShell)
# Run from project root: .\start_backend.ps1

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  DocuSentinel AI - Backend Startup" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# 1. Check for .env
if (-not (Test-Path "backend\.env")) {
    Write-Host ""
    Write-Host "[WARN] backend\.env not found." -ForegroundColor Yellow
    Write-Host "       Copy .env.example to backend\.env and add your OPENAI_API_KEY." -ForegroundColor Yellow
    Write-Host "       The system will still run using local embeddings (no API key needed)." -ForegroundColor Yellow
    Write-Host ""
}

# 2. Check for venv
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Green
    python -m venv venv
}

# 3. Activate venv
Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Green
& "venv\Scripts\Activate.ps1"

# 4. Install dependencies
Write-Host "[INFO] Installing backend dependencies..." -ForegroundColor Green
pip install -r backend\requirements.txt --quiet

# 5. Ensure data dirs exist
New-Item -ItemType Directory -Force -Path "data\uploads"     | Out-Null
New-Item -ItemType Directory -Force -Path "data\vectorstore" | Out-Null

# 6. Start FastAPI
Write-Host ""
Write-Host "[INFO] Starting DocuSentinel AI backend on http://localhost:8000" -ForegroundColor Green
Write-Host "[INFO] API docs available at http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host ""

Set-Location backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
