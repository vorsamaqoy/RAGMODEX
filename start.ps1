# Start RAGMODEX - FastAPI backend + React frontend
$root = $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"
$frontendNodeModules = Join-Path $root "frontend\node_modules"

if (-not (Test-Path $python)) {
  Write-Host "Python virtual environment not found." -ForegroundColor Red
  Write-Host "Create it with: python -m venv venv"
  Write-Host "Then install dependencies with: venv\Scripts\pip install -r requirements.txt"
  exit 1
}

if (-not (Test-Path $frontendNodeModules)) {
  Write-Host "Frontend dependencies not found." -ForegroundColor Red
  Write-Host "Run first: cd frontend; npm install"
  exit 1
}

Write-Host "Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process -FilePath $python `
  -ArgumentList "-m", "uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" `
  -WorkingDirectory $root `
  -WindowStyle Minimized

Start-Sleep -Seconds 2

Write-Host "Starting React frontend on http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" `
  -ArgumentList "/c", "cd /d `"$root\frontend`" && npm run dev" `
  -WorkingDirectory "$root\frontend" `
  -WindowStyle Minimized

Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "RAGMODEX is starting up:" -ForegroundColor Green
Write-Host "  Backend API:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend:     http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Close the backend/frontend terminal windows to stop the app." -ForegroundColor Gray
