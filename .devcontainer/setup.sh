#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"
python -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m playwright install --with-deps chromium
cd ../frontend && npm install
