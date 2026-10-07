#!/usr/bin/env bash
# Выполняется НА СЕРВЕРЕ от root. Его запускает GitHub Actions (workflow «Deploy»), но можно и вручную:
#   REPO_URL=https://github.com/OWNER/REPO.git GIT_SHA=main DOMAIN=example.ru ADMIN_LOGIN=admin ADMIN_PASSWORD=... bash deploy/remote-deploy.sh
# Скачивает нужную версию кода в /opt/norma, при первом запуске ставит Docker и всё настраивает, иначе обновляет.
# Файл .env и папка backups/ в /opt/norma не затираются.
set -euo pipefail
: "${REPO_URL:?не задан REPO_URL}" "${GIT_SHA:?не задан GIT_SHA}"
APP_DIR="${APP_DIR:-/opt/norma}"
if [ "$(id -u)" -ne 0 ]; then echo "Запустите от root."; exit 1; fi
if [ -n "${DOMAIN:-}" ]; then
  DOMAIN="$(printf '%s' "$DOMAIN" | tr -d '\r[:space:]' | tr 'A-Z' 'a-z' | sed -E 's#^https?://##; s#/.*$##; s#^www\.##')"
  if ! printf '%s' "$DOMAIN" | grep -Eq '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'; then
    echo "Домен «$DOMAIN» выглядит неверно. Нужен вид norma-audit.ru (для .рф — в виде xn--...)."; exit 1
  fi
fi
export DEBIAN_FRONTEND=noninteractive

echo "==> Код из $REPO_URL ($GIT_SHA)"
command -v git >/dev/null 2>&1 || { apt-get update -y && apt-get install -y git; }
mkdir -p "$APP_DIR"
cd "$APP_DIR"
[ -d .git ] || git init -q
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
git fetch -q --depth 1 origin "$GIT_SHA"
git checkout -q -f FETCH_HEAD
echo "    версия: $(git log -1 --format='%h %s')"

# Записать KEY='значение' в .env (заменить строку или добавить)
set_env() {
  local k="$1" v="$2"
  case "$v" in *"'"*|*$'\n'*) echo "    ! $k содержит апостроф или перевод строки — не записываю"; return 0 ;; esac
  if grep -q "^$k=" .env; then
    K="$k" L="$k='$v'" awk 'BEGIN { k = ENVIRON["K"] "="; l = ENVIRON["L"] } index($0, k) == 1 { print l; next } { print }' .env > .env.tmp
    cat .env.tmp > .env && rm -f .env.tmp
  else
    printf "%s='%s'\n" "$k" "$v" >> .env
  fi
}

FIRST_RUN=1
if [ -f .env ] && docker compose version >/dev/null 2>&1; then FIRST_RUN=0; fi

if [ -f .env ]; then
  echo "==> Обновляю настройки в .env из GitHub"
  if [ -n "${DOMAIN:-}" ]; then
    set_env DOMAIN "$DOMAIN"
    set_env PUBLIC_BASE_URL "https://$DOMAIN"
  fi
  if [ -n "${ADMIN_LOGIN:-}" ]; then set_env ADMIN_LOGIN "$ADMIN_LOGIN"; fi
  if [ -n "${ADMIN_PASSWORD:-}" ]; then set_env ADMIN_PASSWORD "$ADMIN_PASSWORD"; fi
else
  echo "==> Создаю .env (пароли базы и ключи генерируются на сервере и никуда не передаются)"
  bash deploy/gen-env.sh </dev/null
fi

# Необязательные ключи и реквизиты: пустые значения не трогают то, что уже есть в .env
for k in OPENROUTER_API_KEY YOOKASSA_SHOP_ID YOOKASSA_SECRET_KEY DADATA_API_KEY \
         OPERATOR_NAME OPERATOR_INN OPERATOR_OGRN OPERATOR_ADDRESS OPERATOR_EMAIL; do
  if [ -n "${!k:-}" ]; then set_env "$k" "${!k}"; echo "    $k задан"; fi
done

if [ "$FIRST_RUN" = 1 ]; then
  echo "==> Первая установка: Docker, файрвол, сборка (5–15 минут)"
  bash deploy/setup-server.sh </dev/null
else
  echo "==> Обновление: бэкап базы, сборка, перезапуск"
  bash deploy/update.sh </dev/null
fi

set -a; . ./.env; set +a
echo "==> Жду, пока сайт ответит по https://$DOMAIN (сертификат выпускается 1–3 минуты)"
for _ in $(seq 1 36); do
  curl -fsS -m 10 -o /dev/null "https://$DOMAIN/api/prices" 2>/dev/null && break
  sleep 5
done

echo "==> Проверка"
bash deploy/smoke.sh </dev/null
echo
echo "Сайт:    https://$DOMAIN"
echo "Админка: https://$DOMAIN/login  (логин ${ADMIN_LOGIN:-из .env}, пароль — из секрета ADMIN_PASSWORD)"
