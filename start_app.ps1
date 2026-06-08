$ErrorActionPreference = "Stop"
if (-Not (Test-Path ".venv")) {
    throw "Virtual environment not found. Run .\setup.ps1 first."
}

$root = (Get-Location).Path
$backend = "Set-Location '$root'; & .\.venv\Scripts\Activate.ps1; python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
$frontend = "Set-Location '$root'; npm --prefix frontend run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backend
Start-Sleep -Seconds 3
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontend
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Green
