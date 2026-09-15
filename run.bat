@echo off
cd /d "%~dp0"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r backend\requirements.txt
if not exist .env copy .env.example .env
echo PraroopAI -^> http://localhost:8080  (set LOG_LEVEL=DEBUG in .env for verbose logs)
uvicorn backend.app:app --reload --port 8080
