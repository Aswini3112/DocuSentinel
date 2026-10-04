# DocuSentinel AI - Frontend Startup Script (Windows PowerShell)
# Run from project root: .\start_frontend.ps1
# Requires: Node.js 18+ and npm

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DocuSentinel AI - Frontend Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Set-Location frontend

# Check for node_modules
if (-not (Test-Path "node_modules")) {
    Write-Host "[INFO] Installing frontend dependencies..." -ForegroundColor Green
    npm install
}

Write-Host ""
Write-Host "[INFO] Starting DocuSentinel AI frontend on http://localhost:5173" -ForegroundColor Green
Write-Host "[INFO] Proxying /api requests to http://localhost:8000" -ForegroundColor Cyan
Write-Host ""

npm run dev
