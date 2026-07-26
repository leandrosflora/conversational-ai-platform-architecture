#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${ALLOW_DESTRUCTIVE_RESTORE:-false}" != "true" ]]; then
  echo "ERROR: DR drill destrutivo. Execute com ALLOW_DESTRUCTIVE_RESTORE=true." >&2
  exit 2
fi

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.override.yml")
RUN_ID=${RUN_ID:-"dr-$(date -u +%Y%m%dT%H%M%SZ)"}
EVIDENCE_DIR=${EVIDENCE_DIR:-"$ROOT/artifacts/dr/$RUN_ID"}
BACKUP_ROOT=${BACKUP_ROOT:-"$ROOT/backups"}
BACKUP_DIR="$BACKUP_ROOT/$RUN_ID"
mkdir -p "$EVIDENCE_DIR"

cleanup() {
  local exit_code=$?
  if (( exit_code != 0 )); then
    "${COMPOSE[@]}" ps >"$EVIDENCE_DIR/compose-ps.txt" 2>&1 || true
    "${COMPOSE[@]}" logs --no-color --tail=400 >"$EVIDENCE_DIR/compose-logs.txt" 2>&1 || true
  fi
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  exit "$exit_code"
}
trap cleanup EXIT

cd "$ROOT"
scripts/write-ci-env.sh
STARTED_AT=$(date +%s)
"${COMPOSE[@]}" up -d --wait postgres mongodb redis opensearch kafka kafka-init

"${COMPOSE[@]}" exec -T postgres psql -U postgres -d conversational_ai <<SQL
create schema if not exists ops;
create table if not exists ops.dr_sentinel (
  run_id text primary key,
  payload text not null,
  created_at timestamptz not null default now()
);
insert into ops.dr_sentinel(run_id, payload)
values ('$RUN_ID', 'persist-me')
on conflict (run_id) do update set payload = excluded.payload;
SQL

"${COMPOSE[@]}" exec -T mongodb mongosh \
  --quiet \
  --username admin \
  --password admin \
  --authenticationDatabase admin \
  conversational_ai \
  --eval "db.dr_sentinel.updateOne({_id:'$RUN_ID'},{\$set:{payload:'persist-me'}},{upsert:true}); printjson(db.dr_sentinel.findOne({_id:'$RUN_ID'}));" \
  >"$EVIDENCE_DIR/mongodb-seed.json"

POSTGRES_BEFORE=$("${COMPOSE[@]}" exec -T postgres psql -U postgres -d conversational_ai -Atc \
  "select count(*) from ops.dr_sentinel where run_id='$RUN_ID' and payload='persist-me';")
MONGO_BEFORE=$("${COMPOSE[@]}" exec -T mongodb mongosh --quiet --username admin --password admin \
  --authenticationDatabase admin conversational_ai --eval \
  "print(db.dr_sentinel.countDocuments({_id:'$RUN_ID',payload:'persist-me'}));")
test "$POSTGRES_BEFORE" = "1"
test "$MONGO_BEFORE" = "1"

BACKUP_ROOT="$BACKUP_ROOT" scripts/backup-local.sh "$RUN_ID"
cp "$BACKUP_DIR/SHA256SUMS" "$EVIDENCE_DIR/backup-sha256sums.txt"
BACKUP_COMPLETED_AT=$(date +%s)

"${COMPOSE[@]}" down -v --remove-orphans
DESTRUCTION_COMPLETED_AT=$(date +%s)

ALLOW_DESTRUCTIVE_RESTORE=true scripts/restore-local.sh "$BACKUP_DIR"
RESTORE_COMPLETED_AT=$(date +%s)

POSTGRES_AFTER=$("${COMPOSE[@]}" exec -T postgres psql -U postgres -d conversational_ai -Atc \
  "select count(*) from ops.dr_sentinel where run_id='$RUN_ID' and payload='persist-me';")
MONGO_AFTER=$("${COMPOSE[@]}" exec -T mongodb mongosh --quiet --username admin --password admin \
  --authenticationDatabase admin conversational_ai --eval \
  "print(db.dr_sentinel.countDocuments({_id:'$RUN_ID',payload:'persist-me'}));")
test "$POSTGRES_AFTER" = "1"
test "$MONGO_AFTER" = "1"

# Kafka and OpenSearch are explicitly reconstruction-based in this workspace.
"${COMPOSE[@]}" up -d --wait opensearch kafka kafka-init
TOPIC_COUNT=$("${COMPOSE[@]}" exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list \
  | grep -Ec '^(channel\.|intent\.detected$|conversation\.state_changed$|agent\.events$|tool\.executed$)')
test "$TOPIC_COUNT" -ge 9
curl --fail --silent --show-error http://localhost:9200/_cluster/health >"$EVIDENCE_DIR/opensearch-cluster-health.json"

FINISHED_AT=$(date +%s)
RTO_SECONDS=$((RESTORE_COMPLETED_AT - DESTRUCTION_COMPLETED_AT))
TOTAL_SECONDS=$((FINISHED_AT - STARTED_AT))
cat >"$EVIDENCE_DIR/dr-result.json" <<JSON
{
  "runId": "$RUN_ID",
  "postgresSentinelBefore": $POSTGRES_BEFORE,
  "postgresSentinelAfter": $POSTGRES_AFTER,
  "mongoSentinelBefore": $MONGO_BEFORE,
  "mongoSentinelAfter": $MONGO_AFTER,
  "kafkaTopicCountAfterReconstruction": $TOPIC_COUNT,
  "backupDurationSeconds": $((BACKUP_COMPLETED_AT - STARTED_AT)),
  "rtoSeconds": $RTO_SECONDS,
  "totalDrillSeconds": $TOTAL_SECONDS,
  "rpo": "zero-for-seeded-sentinels",
  "result": "passed"
}
JSON

"${COMPOSE[@]}" ps >"$EVIDENCE_DIR/compose-final.txt"
echo "OK: DR invariants restored; RTO=${RTO_SECONDS}s; evidence=$EVIDENCE_DIR"
