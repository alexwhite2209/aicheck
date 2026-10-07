#!/usr/bin/env bash
# Создаёт .env с надёжными случайными паролями. Спрашивает только домен и логин администратора.
# Без вопросов (GitHub Actions): заранее задайте переменные DOMAIN, ADMIN_LOGIN и ADMIN_PASSWORD.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { echo ".env уже существует — ничего не меняю."; exit 0; }

rand() { openssl rand -hex "$1"; }

# убираем \r, невидимый BOM и пробелы из введённого
clean() { printf '%s' "$1" | tr -d '\r' | sed -E $'s/^\xEF\xBB\xBF//; s/^[[:space:]]+//; s/[[:space:]]+$//'; }

DOMAIN="${DOMAIN:-}"
ADMIN_LOGIN="${ADMIN_LOGIN:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
PRINT_PASSWORD=0

[ -n "$DOMAIN" ] || read -r -p "Домен сайта (например, norma-audit.ru; A-запись должна указывать на этот сервер): " DOMAIN
DOMAIN="$(clean "$DOMAIN" | tr 'A-Z' 'a-z' | sed -E 's#^https?://##; s#/.*$##; s#^www\.##')"
if ! printf '%s' "$DOMAIN" | grep -Eq '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'; then
  echo "Домен «$DOMAIN» выглядит неверно. Нужен вид norma-audit.ru. Для кириллического домена (.рф) введите его в латинской форме (xn--...)."
  exit 1
fi

[ -n "$ADMIN_LOGIN" ] || read -r -p "Логин администратора (для входа в /admin, например admin): " ADMIN_LOGIN
ADMIN_LOGIN="$(clean "$ADMIN_LOGIN" | tr 'A-Z' 'a-z')"
if ! printf '%s' "$ADMIN_LOGIN" | grep -Eq '^[a-z0-9_.-]{3,32}$'; then
  echo "Логин «$ADMIN_LOGIN» не подходит: 3–32 символа, латиница, цифры, точка, дефис или подчёркивание."; exit 1
fi

if [ -z "$ADMIN_PASSWORD" ]; then
  ADMIN_PASSWORD="$(rand 10)"
  PRINT_PASSWORD=1
elif [ "${#ADMIN_PASSWORD}" -lt 8 ]; then
  echo "Пароль администратора должен быть не короче 8 символов."; exit 1
fi
case "$ADMIN_PASSWORD" in
  *$'\n'*|*'"'*|*"'"*|*'$'*|*'`'*|*'\'*) echo "Пароль администратора не должен содержать кавычки, \$, \` и \\."; exit 1 ;;
esac

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

ADMIN_LOGIN=${ADMIN_LOGIN}
ADMIN_PASSWORD='${ADMIN_PASSWORD}'

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
OPERATOR_EMAIL=
EOF
chmod 600 .env

echo
echo "=============================================================="
echo " Вход в админку:  https://${DOMAIN}/login"
echo "   логин:  ${ADMIN_LOGIN}"
if [ "$PRINT_PASSWORD" = 1 ]; then
  echo "   пароль: ${ADMIN_PASSWORD}   (запишите, повторно не покажем)"
else
  echo "   пароль: тот, что вы задали"
fi
echo "=============================================================="
echo "Реквизиты OPERATOR_* заполните в .env позже (nano .env), затем: docker compose up -d --build frontend"
