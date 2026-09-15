#!/usr/bin/env bash
set -e
#cd "$(dirname "$0")"
#[ -d .venv ] || python3 -m venv .venv
#source .venv/bin/activate
#pip install -q -r backend/requirements.txt
#[ -f .env ] || cp .env.example .env
PORT="${PRAROOP_PORT:-8080}"
echo "PraroopAI -> http://localhost:$PORT   (set LOG_LEVEL=DEBUG in .env for verbose logs)"
uvicorn backend.app:app --reload --port "$PORT"
