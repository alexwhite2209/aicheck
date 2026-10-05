#!/usr/bin/env bash
# Установка зависимостей. Каждый шаг пишет, что делает; сбой Chromium не мешает поднять сам сайт.
set -u
root="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> backend: Python-зависимости"
cd "$root/backend"
python -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt || { echo "ОШИБКА: pip install не удался"; exit 1; }

echo "==> Chromium для Playwright (нужен для проверки сайтов)"
.venv/bin/python -m playwright install chromium || echo "ПРЕДУПРЕЖДЕНИЕ: не удалось скачать Chromium"
# системные библиотеки Chromium требуют root
sudo -n .venv/bin/python -m playwright install-deps chromium || echo "ПРЕДУПРЕЖДЕНИЕ: не удалось поставить системные библиотеки Chromium"

echo "==> frontend: npm install"
cd "$root/frontend"
npm install || { echo "ОШИБКА: npm install не удался"; exit 1; }
echo "==> Готово"
