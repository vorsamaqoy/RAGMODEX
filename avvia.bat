@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
  echo Python virtual environment not found.
  echo Create it with: python -m venv venv
  echo Then install dependencies with: venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)

if not exist "frontend\node_modules" (
  echo Frontend dependencies not found.
  echo Run first: cd frontend ^&^& npm install
  pause
  exit /b 1
)

echo Starting RAGMODEX backend on http://127.0.0.1:8000 ...
start "RAGMODEX Backend" /min venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

timeout /t 3 /nobreak >nul

echo Starting RAGMODEX frontend on http://127.0.0.1:5173 ...
start "RAGMODEX Frontend" /min cmd /c "cd /d frontend && npm run dev -- --host 127.0.0.1 --port 5173"

timeout /t 4 /nobreak >nul

echo Opening browser...
start http://localhost:5173

echo.
echo RAGMODEX is starting at http://localhost:5173
echo API docs: http://localhost:8000/docs
echo Close the backend/frontend terminal windows to stop the app.
pause
