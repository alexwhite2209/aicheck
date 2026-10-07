#!/usr/bin/env bash
# Резервная копия базы PostgreSQL. Хранит 14 последних копий в ./backups
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
set -a; . ./.env; set +a
FILE="backups/norma-$(date +%F-%H%M).sql.gz"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-norma}" "${POSTGRES_DB:-norma}" | gzip > "$FILE"
chmod 600 "$FILE"
ls -1t backups/norma-*.sql.gz | tail -n +15 | xargs -r rm -f
echo "$(date -u +%FT%TZ) OK $FILE ($(du -h "$FILE" | cut -f1))"
