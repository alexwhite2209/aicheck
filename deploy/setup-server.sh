#!/usr/bin/env bash
# Первичная настройка чистого сервера Ubuntu 22.04/24.04 (REG.RU VPS) и запуск «Нормы».
# Запуск от root из папки проекта:  bash deploy/setup-server.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then echo "Запустите от root (sudo -i)."; exit 1; fi
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
echo "==> Папка проекта: $ROOT"

echo "==> 1/6 Обновление системы и базовые пакеты"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl ufw cron openssl

echo "==> 2/6 Docker"
if ! docker compose version >/dev/null 2>&1; then
  # сначала из репозиториев Ubuntu (надёжнее из РФ), затем официальный скрипт
  apt-get install -y docker.io docker-compose-v2 || true
  if ! docker compose version >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
  fi
fi
systemctl enable --now docker

# Зеркало Docker Hub: образы из РФ иногда тянутся нестабильно
if [ ! -f /etc/docker/daemon.json ]; then
  mkdir -p /etc/docker
  cat > /etc/docker/daemon.json <<'JSON'
{ "registry-mirrors": ["https://mirror.gcr.io"], "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "5" } }
JSON
  systemctl restart docker
fi
docker compose version

echo "==> 3/6 Файрвол (открыты только SSH, 80 и 443; база и Redis наружу не опубликованы)"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
ufw status | head -8

echo "==> 4/6 Настройки (.env)"
if [ ! -f .env ]; then
  bash deploy/gen-env.sh
else
  echo ".env уже есть — оставляю как есть."
fi
chmod 600 .env

echo "==> 5/6 Сборка и запуск (первый раз 5–15 минут: собирается сайт и браузер Chromium)"
docker compose up -d --build

echo "==> 6/6 Ежедневный бэкап базы (03:15, хранится 14 копий)"
mkdir -p "$ROOT/backups"
CRON_LINE="15 3 * * * cd $ROOT && bash deploy/backup.sh >> $ROOT/backups/backup.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'deploy/backup.sh' ; echo "$CRON_LINE" ) | crontab -

echo
echo "Готово. Проверка:  bash deploy/smoke.sh"
DOMAIN_VAL="$(grep -E '^DOMAIN=' .env | cut -d= -f2-)"
echo "Сайт:  https://${DOMAIN_VAL}   (сертификат выпускается автоматически за 1–2 минуты после первого открытия)"
