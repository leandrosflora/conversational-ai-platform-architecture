#!/usr/bin/env bash
set -Eeuo pipefail

ARCH_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ARTIFACT_DIR=${ARTIFACT_DIR:-"$ARCH_ROOT/artifacts/e2e"}
COMPOSE=(docker compose -f "$ARCH_ROOT/docker-compose.yml" -f "$ARCH_ROOT/docker-compose.override.yml")
RUN_ID=${RUN_ID:-"p8-$(date -u +%Y%m%dT%H%M%SZ)"}
mkdir -p "$ARTIFACT_DIR"

cleanup() {
  local exit_code=$?
  if (( exit_code != 0 )); then
    "${COMPOSE[@]}" ps >"$ARTIFACT_DIR/p8-compose-ps.txt" 2>&1 || true
    "${COMPOSE[@]}" logs --no-color --tail=500 >"$ARTIFACT_DIR/p8-compose-logs.txt" 2>&1 || true
  fi
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  exit "$exit_code"
}
trap cleanup EXIT

wait_http() {
  local name=$1
  local url=$2
  for _ in $(seq 1 120); do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null; then
      echo "OK: $name"
      return 0
    fi
    sleep 2
  done
  echo "ERROR: timeout waiting for $name at $url" >&2
  return 1
}

cd "$ARCH_ROOT"
python scripts/validate-executable-contracts.py | tee "$ARTIFACT_DIR/executable-contracts.txt"
python scripts/run-evals.py --mode offline --output "$ARTIFACT_DIR/evals-offline.json"

# The established E2E remains the primary build and functional evidence. Load is executed below
# with signed unique messages so the original readiness baseline is disabled here.
RUN_LOAD_TEST=false scripts/e2e-multirepo.sh

if [[ "${RUN_ONLINE_EVALS:-true}" != "true" && "${RUN_LOAD_TEST:-true}" != "true" ]]; then
  echo "OK: online evals and load explicitly disabled"
  trap - EXIT
  exit 0
fi

scripts/write-ci-env.sh
set -a
source .env
set +a
"${COMPOSE[@]}" up -d --build
wait_http "whatsapp-bff" "http://localhost:5153/health/ready"
wait_http "renegotiation agent" "http://localhost:8100/health/ready"
wait_http "card agent" "http://localhost:8110/health/ready"
wait_http "orchestrator" "http://localhost:5268/health/ready"

if [[ "${RUN_ONLINE_EVALS:-true}" == "true" ]]; then
  python scripts/run-evals.py --mode online --output "$ARTIFACT_DIR/evals-online.json"
fi

if [[ "${RUN_LOAD_TEST:-true}" == "true" ]]; then
  export RUN_ID
  docker run --rm --network host \
    -e BASE_URL=http://localhost:5153 \
    -e WHATSAPP_APP_SECRET="$WHATSAPP_APP_SECRET" \
    -e RUN_ID="$RUN_ID" \
    -e E2E_PHONE_NUMBER="${E2E_PHONE_NUMBER:-5511999999999}" \
    -e VUS="${K6_VUS:-5}" \
    -e DURATION="${K6_DURATION:-20s}" \
    -v "$ARCH_ROOT/tests/load:/tests:ro" \
    grafana/k6:2.0.0 run /tests/journey.js \
    | tee "$ARTIFACT_DIR/k6-signed-journey.txt"

  # Kafka delivery is asynchronous. Wait until at least one k6 message reaches the durable Inbox.
  K6_INBOX_COUNT=0
  for _ in $(seq 1 90); do
    K6_INBOX_COUNT=$("${COMPOSE[@]}" exec -T postgres psql -U postgres -d conversational_ai -Atc \
      "select count(*) from ops.message_inbox where message_id like 'wamid.k6-${RUN_ID}-%';" \
      2>/dev/null || echo 0)
    if [[ "$K6_INBOX_COUNT" =~ ^[0-9]+$ ]] && (( K6_INBOX_COUNT > 0 )); then
      break
    fi
    sleep 2
  done
  test "$K6_INBOX_COUNT" =~ ^[0-9]+$
  (( K6_INBOX_COUNT > 0 ))
  printf '{"runId":"%s","inboxMessages":%s}\n' "$RUN_ID" "$K6_INBOX_COUNT" \
    >"$ARTIFACT_DIR/k6-durable-inbox-evidence.json"
fi

"${COMPOSE[@]}" ps >"$ARTIFACT_DIR/p8-compose-final.txt"
curl --fail --silent --show-error http://localhost:9090/api/v1/alerts >"$ARTIFACT_DIR/p8-prometheus-alerts.json"
trap - EXIT
"${COMPOSE[@]}" down -v --remove-orphans

echo "OK: release lock, executable contracts, evals and signed journey load completed"
