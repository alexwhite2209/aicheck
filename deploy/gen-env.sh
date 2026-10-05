#!/usr/bin/env bash
# Создаёт .env с надёжными случайными паролями. Спрашивает только домен и email администратора.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { echo ".env уже существует — ничего не меняю."; exit 0; }

rand() { openssl rand -hex "$1"; }

# убираем \r, невидимый BOM и пробелы из введённого
clean() { printf '%s' "$1" | tr -d '\r' | sed -E $'s/^\xEF\xBB\xBF//; s/^[[:space:]]+//; s/[[:space:]]+$//'; }

read -r -p "Домен сайта (например, norma-audit.ru; A-запись должна указывать на этот сервер): " DOMAIN
DOMAIN="$(clean "$DOMAIN" | sed -E 's#^https?://##; s#/.*$##; s#^www\.##' | tr 'A-Z' 'a-z')"
if ! printf '%s' "$DOMAIN" | grep -Eq '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'; then
  echo "Домен «$DOMAIN» выглядит неверно. Нужен вид norma-audit.ru. Для кириллического домена (.рф) введите его в латинской форме (xn--...)."
  exit 1
fi

read -r -p "Email администратора (для входа в /admin): " ADMIN_EMAIL
ADMIN_EMAIL="$(clean "$ADMIN_EMAIL")"
if ! printf '%s' "$ADMIN_EMAIL" | grep -Eq '^[^@ ]+@[^@ ]+\.[^@ ]+$'; then
  echo "Email «$ADMIN_EMAIL» выглядит неверно."; exit 1
fi
ADMIN_PASSWORD="$(rand 10)"

cat > .env <<EOF
# Создано $(date -u +%F) — не публикуйте этот файл и не добавляйте в Git
DOMAIN=${DOMAIN}
PUBLIC_BASE_URL=https://${DOMAIN}
TRUST_PROXY_HEADERS=true

POSTGRES_DB=norma
POSTGRES_USER=norma
POSTGRES_PASSWORD=$(rand 24)
JWT_SECRET=$(rand 32)
IP_HASH_SECRET=$(rand 32)

ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# AI-объяснения (необязательно). Без ключа отчёты строятся по шаблонам правил
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini

# Оплата ЮKassa (необязательно). Пока пусто — полный отчёт открыт всем
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=

# Проверка ЕГРЮЛ/ЕГРИП (бесплатный ключ DaData, необязательно)
DADATA_API_KEY=

# Реквизиты владельца сервиса — попадают в политику, согласие и соглашение на сайте
OPERATOR_NAME=
OPERATOR_INN=
OPERATOR_OGRN=
OPERATOR_ADDRESS=
OPERATOR_EMAIL=${ADMIN_EMAIL}
EOF
chmod 600 .env

echo
echo "=============================================================="
echo " Данные для входа в админку (запишите, повторно не покажем):"
echo "   адрес:  https://${DOMAIN}/login"
echo "   email:  ${ADMIN_EMAIL}"
echo "   пароль: ${ADMIN_PASSWORD}"
echo "=============================================================="
echo "Реквизиты OPERATOR_* заполните в .env позже (nano .env), затем: docker compose up -d --build frontend"
