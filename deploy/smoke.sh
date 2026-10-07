#!/usr/bin/env bash
# Проверка после запуска: все контейнеры работают, сайт и API отвечают, реальная проверка сайта проходит.
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
BASE="https://${DOMAIN}"
ok=0; fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; ok=$((ok+1)); else echo "  ✗ $1"; fail=$((fail+1)); fi; }

echo "Контейнеры:"
docker compose ps --format '  {{.Service}}: {{.State}} {{.Health}}'
echo
echo "Проверки:"
check "backend отвечает (health)"          "docker compose exec -T backend python -c \"import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')\""
check "главная открывается по HTTPS"        "curl -fsS -m 20 -o /dev/null $BASE/"
check "API через сайт (цены)"               "curl -fsS -m 20 $BASE/api/prices | grep -q all_in_one"
check "страница методики (правила из базы)" "curl -fsS -m 20 $BASE/api/public/rules | grep -q 152FZ"
check "SSRF-защита: localhost отклонён"     "test \"\$(curl -s -m 20 -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{\"url\":\"http://127.0.0.1/\"}' $BASE/api/audit)\" = 422"

echo
echo "Тестовая проверка сайта example.com (до 2 минут)..."
ID=$(curl -fsS -m 30 -X POST -H 'Content-Type: application/json' -d '{"url":"example.com"}' "$BASE/api/audit" | sed -E 's/.*"id":"([a-f0-9]+)".*/\1/')
if [ -n "$ID" ]; then
  for i in $(seq 1 50); do
    S=$(curl -fsS -m 20 "$BASE/api/audit/$ID/status" | sed -E 's/.*"status":"([a-z]+)".*/\1/')
    [ "$S" = "done" ] || [ "$S" = "failed" ] && break
    sleep 3
  done
  check "проверка сайта дошла до конца (status=$S)" "test '$S' = done"
  [ "$S" = "done" ] && check "PDF формируется" "curl -fsS -m 60 $BASE/api/report/$ID/pdf | head -c 4 | grep -q PDF"
fi

echo
echo "Итог: $ok успешно, $fail с ошибкой."
[ "$fail" -eq 0 ] || { echo "Смотрите логи:  docker compose logs --tail 80 backend worker caddy"; exit 1; }
