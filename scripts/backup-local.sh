#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.override.yml")
BACKUP_ROOT=${BACKUP_ROOT:-"$ROOT/backups"}
STAMP=${1:-$(date -u +%Y%m%dT%H%M%SZ)}
DEST="$BACKUP_ROOT/$STAMP"

mkdir -p "$DEST"

"${COMPOSE[@]}" exec -T postgres pg_dump -U postgres -d conversational_ai -Fc >"$DEST/postgres.dump"
"${COMPOSE[@]}" exec -T mongodb mongodump \
  --username admin \
  --password admin \
  --authenticationDatabase admin \
  --db conversational_ai \
  --archive \
  --gzip >"$DEST/mongodb.archive.gz"

"${COMPOSE[@]}" exec -T redis redis-cli INFO persistence >"$DEST/redis-persistence.txt"
"${COMPOSE[@]}" exec -T redis redis-cli DBSIZE >"$DEST/redis-dbsize.txt"

curl --fail --silent --show-error http://localhost:9200/_cat/indices?format=json \
  >"$DEST/opensearch-indices.json"
"${COMPOSE[@]}" exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --describe \
  >"$DEST/kafka-topics.txt"

cp "$ROOT/docker-compose.yml" "$DEST/"
cp "$ROOT/docker-compose.override.yml" "$DEST/"
cp "$ROOT/.env" "$DEST/env.redacted"
sed -i -E 's/^([^=]*(SECRET|KEY|PASSWORD|TOKEN)[^=]*)=.*/\1=<redacted>/I' "$DEST/env.redacted"

(
  cd "$DEST"
  sha256sum postgres.dump mongodb.archive.gz redis-persistence.txt redis-dbsize.txt \
    opensearch-indices.json kafka-topics.txt docker-compose.yml docker-compose.override.yml \
    env.redacted >SHA256SUMS
)

echo "Backup local criado em $DEST"
echo "Redis, OpenSearch e Kafka são registrados como inventário/reconstruíveis. O restore automatizado cobre PostgreSQL e MongoDB."
