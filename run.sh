#!/usr/bin/env bash
# PraroopAI launcher
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r backend/requirements.txt
[ -f .env ] || cp .env.example .env
echo "PraroopAI -> http://localhost:${PRAROOP_PORT:-8080}"
uvicorn backend.app:app --reload --port "${PRAROOP_PORT:-8080}"
