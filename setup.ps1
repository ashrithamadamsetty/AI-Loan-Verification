$ErrorActionPreference = "Stop"
Write-Host "Setting up the local Loan Verification application..." -ForegroundColor Cyan

if (-Not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
npm --prefix frontend install

if (-Not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example" -ForegroundColor Yellow
}

python scripts\init_local.py
Write-Host "Setup complete. Add GEMINI_API_KEY to .env, then run .\start_app.ps1" -ForegroundColor Green
