#!/usr/bin/env bash
# Запускает backend (:8000) и frontend (:3000) в фоне; логи в /tmp/norma-*.log
root="$(cd "$(dirname "$0")/.." && pwd)"
export TASK_MODE=inline ENV=development
export JWT_SECRET="${JWT_SECRET:-dev-only-secret-change-me-0123456789abcdef}"
export ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}" ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin12345}"
cd "$root/backend" && nohup .venv/bin/python -m uvicorn app.main:app --port 8000 >/tmp/norma-backend.log 2>&1 &
cd "$root/frontend" && nohup npm run dev >/tmp/norma-frontend.log 2>&1 &
