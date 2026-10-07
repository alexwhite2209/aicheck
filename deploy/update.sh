#!/usr/bin/env bash
# Обновление после загрузки новой версии файлов проекта: делает бэкап, пересобирает и перезапускает.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "==> Бэкап базы перед обновлением"
bash deploy/backup.sh || echo "(бэкап пропущен — база ещё не запущена?)"
echo "==> Пересборка и перезапуск"
docker compose up -d --build
docker image prune -f >/dev/null
echo "==> Готово. Проверка: bash deploy/smoke.sh"
