@echo off
REM PraroopAI launcher (Windows)
cd /d "%~dp0"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r backend\requirements.txt
if not exist .env copy .env.example .env
echo PraroopAI -^> http://localhost:8080
uvicorn backend.app:app --reload --port 8080
