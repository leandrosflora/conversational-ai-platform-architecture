#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${ALLOW_DESTRUCTIVE_DRILL:-false}" != "true" ]]; then
  echo "ERROR: chaos drill bloqueado. Execute com ALLOW_DESTRUCTIVE_DRILL=true." >&2
  exit 2
fi

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.override.yml")
SCENARIO=${1:-kafka-ack}
RUN_ID=${RUN_ID:-"chaos-$(date -u +%Y%m%dT%H%M%SZ)"}
EVIDENCE_DIR=${EVIDENCE_DIR:-"$ROOT/artifacts/chaos/$RUN_ID-$SCENARIO"}
mkdir -p "$EVIDENCE_DIR"

cleanup() {
  local exit_code=$?
  "${COMPOSE[@]}" unpause kafka conversation-memory-service >/dev/null 2>&1 || true
  if (( exit_code != 0 )); then
    "${COMPOSE[@]}" ps >"$EVIDENCE_DIR/compose-ps.txt" 2>&1 || true
    "${COMPOSE[@]}" logs --no-color --tail=500 >"$EVIDENCE_DIR/compose-logs.txt" 2>&1 || true
  fi
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  exit "$exit_code"
}
trap cleanup EXIT

wait_http() {
  local url=$1
  for _ in $(seq 1 120); do
    curl --fail --silent --show-error --max-time 3 "$url" >/dev/null && return 0
    sleep 2
  done
  return 1
}

make_webhook() {
  local message_id=$1
  local payload_file=$2
  local signature_file=$3
  MESSAGE_ID="$message_id" PAYLOAD_FILE="$payload_file" SIGNATURE_FILE="$signature_file" python - <<'PY'
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

message_id = os.environ["MESSAGE_ID"]
payload = {
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "chaos-account",
        "changes": [{
            "field": "messages",
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {"display_phone_number": "5511000000000", "phone_number_id": "chaos-phone"},
                "contacts": [{"profile": {"name": "Chaos"}, "wa_id": "5511999999999"}],
                "messages": [{
                    "from": "5511999999999",
                    "id": message_id,
                    "timestamp": str(int(time.time())),
                    "type": "text",
                    "text": {"body": "Quero renegociar minha dívida"},
                }],
            },
        }],
    }],
}
raw = json.dumps(payload, separators=(",", ":")).encode()
Path(os.environ["PAYLOAD_FILE"]).write_bytes(raw)
signature = hmac.new(b"placeholder", raw, hashlib.sha256).hexdigest()
Path(os.environ["SIGNATURE_FILE"]).write_text(f"sha256={signature}", encoding="utf-8")
PY
}

send_webhook() {
  local payload_file=$1
  local signature_file=$2
  curl --silent --show-error --max-time 20 \
    --output "$EVIDENCE_DIR/last-webhook-response.json" \
    --write-out '%{http_code}' \
    -H "Content-Type: application/json" \
    -H "X-Hub-Signature-256: $(cat "$signature_file")" \
    --data-binary "@$payload_file" \
    http://localhost:5153/webhooks/whatsapp || true
}

cd "$ROOT"
scripts/write-ci-env.sh
"${COMPOSE[@]}" up -d --build
wait_http http://localhost:5153/health/ready
wait_http http://localhost:5268/health/ready

case "$SCENARIO" in
  kafka-ack)
    FAILED_ID="wamid.${RUN_ID}.kafka-down"
    make_webhook "$FAILED_ID" "$EVIDENCE_DIR/kafka-down.json" "$EVIDENCE_DIR/kafka-down.signature"
    "${COMPOSE[@]}" pause kafka
    STATUS_WHILE_DOWN=$(send_webhook "$EVIDENCE_DIR/kafka-down.json" "$EVIDENCE_DIR/kafka-down.signature")
    test "$STATUS_WHILE_DOWN" != "200"
    "${COMPOSE[@]}" unpause kafka
    sleep 5
    RECOVERY_ID="wamid.${RUN_ID}.kafka-recovered"
    make_webhook "$RECOVERY_ID" "$EVIDENCE_DIR/kafka-recovered.json" "$EVIDENCE_DIR/kafka-recovered.signature"
    STATUS_AFTER_RECOVERY=$(send_webhook "$EVIDENCE_DIR/kafka-recovered.json" "$EVIDENCE_DIR/kafka-recovered.signature")
    test "$STATUS_AFTER_RECOVERY" = "200"
    cat >"$EVIDENCE_DIR/result.json" <<JSON
{"scenario":"kafka-ack","statusWhileKafkaPaused":"$STATUS_WHILE_DOWN","statusAfterRecovery":"$STATUS_AFTER_RECOVERY","invariant":"webhook is never acknowledged when Kafka cannot confirm persistence","result":"passed"}
JSON
    ;;

  outbox-memory-recovery)
    MESSAGE_ID="wamid.${RUN_ID}.memory"
    make_webhook "$MESSAGE_ID" "$EVIDENCE_DIR/memory.json" "$EVIDENCE_DIR/memory.signature"
    "${COMPOSE[@]}" pause conversation-memory-service
    STATUS=$(send_webhook "$EVIDENCE_DIR/memory.json" "$EVIDENCE_DIR/memory.signature")
    test "$STATUS" = "200"

    FAILED_OR_PENDING=0
    for _ in $(seq 1 90); do
      FAILED_OR_PENDING=$("${COMPOSE[@]}" exec -T postgres psql -U postgres -d conversational_ai -Atc \
        "select count(*) from ops.orchestrator_outbox where idempotency_key like '%${MESSAGE_ID}%' and effect_type like 'memory.%' and status in ('pending','publishing','failed');" \
        2>/dev/null || echo 0)
      [[ "$FAILED_OR_PENDING" =~ ^[0-9]+$ ]] && (( FAILED_OR_PENDING > 0 )) && break
      sleep 2
    done
    (( FAILED_OR_PENDING > 0 ))
    "${COMPOSE[@]}" unpause conversation-memory-service

    PUBLISHED=0
    for _ in $(seq 1 120); do
      PUBLISHED=$("${COMPOSE[@]}" exec -T postgres psql -U postgres -d conversational_ai -Atc \
        "select count(*) from ops.orchestrator_outbox where idempotency_key like '%${MESSAGE_ID}%' and effect_type like 'memory.%' and status='published';" \
        2>/dev/null || echo 0)
      [[ "$PUBLISHED" =~ ^[0-9]+$ ]] && (( PUBLISHED > 0 )) && break
      sleep 2
    done
    (( PUBLISHED > 0 ))
    cat >"$EVIDENCE_DIR/result.json" <<JSON
{"scenario":"outbox-memory-recovery","webhookStatus":"$STATUS","blockedEffects":$FAILED_OR_PENDING,"publishedAfterRecovery":$PUBLISHED,"invariant":"accepted effects remain durable and publish after dependency recovery","result":"passed"}
JSON
    ;;

  *)
    echo "ERROR: unsupported scenario $SCENARIO" >&2
    exit 2
    ;;
esac

"${COMPOSE[@]}" ps >"$EVIDENCE_DIR/compose-final.txt"
echo "OK: chaos invariant $SCENARIO passed; evidence=$EVIDENCE_DIR"
