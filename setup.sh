#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
npm --prefix frontend install
if [[ ! -f .env ]]; then cp .env.example .env; fi
python scripts/init_local.py
printf '\nSetup complete. Add GEMINI_API_KEY to .env, then run ./start_app.sh\n'
