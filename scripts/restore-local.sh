#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${ALLOW_DESTRUCTIVE_RESTORE:-false}" != "true" ]]; then
  echo "ERROR: restore é destrutivo. Execute com ALLOW_DESTRUCTIVE_RESTORE=true." >&2
  exit 2
fi

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.override.yml")
SOURCE=${1:?Usage: ALLOW_DESTRUCTIVE_RESTORE=true scripts/restore-local.sh <backup-dir>}

test -f "$SOURCE/SHA256SUMS"
(
  cd "$SOURCE"
  sha256sum -c SHA256SUMS
)

"${COMPOSE[@]}" up -d postgres mongodb
"${COMPOSE[@]}" exec -T postgres dropdb -U postgres --if-exists conversational_ai
"${COMPOSE[@]}" exec -T postgres createdb -U postgres conversational_ai
"${COMPOSE[@]}" exec -T postgres pg_restore -U postgres -d conversational_ai --clean --if-exists \
  <"$SOURCE/postgres.dump"

"${COMPOSE[@]}" exec -T mongodb mongorestore \
  --username admin \
  --password admin \
  --authenticationDatabase admin \
  --archive \
  --gzip \
  --drop <"$SOURCE/mongodb.archive.gz"

echo "Restore local de PostgreSQL e MongoDB concluído."
echo "Redis, Kafka e OpenSearch devem ser reconstruídos a partir dos dados/eventos de origem conforme o runbook."
