#!/usr/bin/env bash
set -Eeuo pipefail

ARCH_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WORKSPACE_ROOT=$(cd "$ARCH_ROOT/.." && pwd)
COMPOSE=(docker compose -f "$ARCH_ROOT/docker-compose.yml" -f "$ARCH_ROOT/docker-compose.override.yml")
ARTIFACT_DIR=${ARTIFACT_DIR:-"$ARCH_ROOT/artifacts/e2e"}
RUN_ID=${RUN_ID:-"e2e-$(date -u +%Y%m%dT%H%M%SZ)"}
MESSAGE_ID="wamid.${RUN_ID}"
PHONE_NUMBER=${E2E_PHONE_NUMBER:-5511999999999}

DOTNET_REPOS=(
  whatsapp-bff
  conversation-orchestrator
  renegotiation-service
  conversation-audit-service
  conversation-handoff-service
  core-bancario-mock
)

PYTHON_REPOS=(
  agent-runtime-renegotiation
  tool-service-renegotiation
  agent-runtime-fatura-cartao
  tool-service-cartao-credito
  knowledge-service
  conversation-memory-service
)

ALL_REPOS=("${DOTNET_REPOS[@]}" "${PYTHON_REPOS[@]}")

mkdir -p "$ARTIFACT_DIR"

cleanup() {
  local exit_code=$?
  if (( exit_code != 0 )); then
    "${COMPOSE[@]}" ps >"$ARTIFACT_DIR/compose-ps.txt" 2>&1 || true
    "${COMPOSE[@]}" logs --no-color --tail=400 >"$ARTIFACT_DIR/compose-logs.txt" 2>&1 || true
  fi
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  exit "$exit_code"
}
trap cleanup EXIT

wait_http() {
  local name=$1
  local url=$2
  local attempts=${3:-120}
  for ((i=1; i<=attempts; i++)); do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null; then
      echo "OK: $name"
      return 0
    fi
    sleep 2
  done
  echo "ERROR: timeout waiting for $name at $url" >&2
  return 1
}

for repo in "${ALL_REPOS[@]}"; do
  test -d "$WORKSPACE_ROOT/$repo/.git" || {
    echo "ERROR: sibling repository missing: $WORKSPACE_ROOT/$repo" >&2
    exit 1
  }
done

echo "## Repository revisions" >"$ARTIFACT_DIR/revisions.md"
for repo in "${ALL_REPOS[@]}"; do
  printf -- '- %s: `%s`\n' "$repo" "$(git -C "$WORKSPACE_ROOT/$repo" rev-parse HEAD)" >>"$ARTIFACT_DIR/revisions.md"
done
printf -- '- conversational-ai-platform-architecture: `%s`\n' "$(git -C "$ARCH_ROOT" rev-parse HEAD)" >>"$ARTIFACT_DIR/revisions.md"

for repo in "${DOTNET_REPOS[@]}"; do
  echo "::group::Build $repo"
  pushd "$WORKSPACE_ROOT/$repo" >/dev/null
  dotnet restore
  dotnet build --no-restore --configuration Release
  mapfile -t tests < <(find . -name '*Tests.csproj' -print)
  if ((${#tests[@]})); then
    dotnet test --no-build --configuration Release
  fi
  popd >/dev/null
  echo "::endgroup::"
done

for repo in "${PYTHON_REPOS[@]}"; do
  echo "::group::Test $repo"
  pushd "$WORKSPACE_ROOT/$repo" >/dev/null
  python -m venv .venv-e2e
  source .venv-e2e/bin/activate
  python -m pip install --upgrade pip
  test ! -f requirements.txt || pip install -r requirements.txt
  test ! -f requirements-dev.txt || pip install -r requirements-dev.txt
  if [[ -d tests ]] && find tests -type f -name 'test_*.py' -print -quit | grep -q .; then
    pytest -q
  else
    echo "No Python tests discovered in $repo; dependencies installed successfully."
  fi
  deactivate
  popd >/dev/null
  echo "::endgroup::"
done

pushd "$ARCH_ROOT" >/dev/null
scripts/write-ci-env.sh
"${COMPOSE[@]}" config --quiet
"${COMPOSE[@]}" up -d --build

wait_http "whatsapp-bff" "http://localhost:5153/health/ready"
wait_http "conversation-orchestrator" "http://localhost:5268/health/ready"
wait_http "agent-runtime-renegotiation" "http://localhost:8100/health/ready"
wait_http "agent-runtime-fatura-cartao" "http://localhost:8110/health/ready"
wait_http "conversation-handoff-service" "http://localhost:8200/health/ready"
wait_http "conversation-audit-service" "http://localhost:8300/health/ready"
wait_http "tool-service-renegotiation" "http://localhost:8401/health/ready"
wait_http "tool-service-cartao-credito" "http://localhost:8411/health/ready"
wait_http "knowledge-service" "http://localhost:8500/health/ready"
wait_http "conversation-memory-service" "http://localhost:8600/health/ready"
wait_http "renegotiation-service" "http://localhost:5266/health/ready"
wait_http "core-bancario-mock" "http://localhost:9401/clients/11111111111"

export MESSAGE_ID PHONE_NUMBER
python - <<'PY'
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

message_id = os.environ["MESSAGE_ID"]
phone = os.environ["PHONE_NUMBER"]
payload = {
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "e2e-account",
        "changes": [{
            "field": "messages",
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "5511000000000",
                    "phone_number_id": "e2e-phone-number-id",
                },
                "contacts": [{"profile": {"name": "E2E"}, "wa_id": phone}],
                "messages": [{
                    "from": phone,
                    "id": message_id,
                    "timestamp": str(int(time.time())),
                    "type": "text",
                    "text": {"body": "Quero consultar minhas opções"},
                }],
            },
        }],
    }],
}
raw = json.dumps(payload, separators=(",", ":")).encode()
secret = "placeholder"
signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
Path("artifacts/e2e/webhook.json").write_bytes(raw)
Path("artifacts/e2e/webhook.signature").write_text(f"sha256={signature}", encoding="utf-8")
PY

curl --fail --silent --show-error \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: $(cat "$ARTIFACT_DIR/webhook.signature")" \
  --data-binary "@$ARTIFACT_DIR/webhook.json" \
  http://localhost:5153/webhooks/whatsapp \
  | tee "$ARTIFACT_DIR/webhook-response.json"

INBOX_COUNT=0
for ((i=1; i<=90; i++)); do
  INBOX_COUNT=$(
    "${COMPOSE[@]}" exec -T postgres psql -U postgres -d conversational_ai -Atc \
      "select count(*) from ops.message_inbox where message_id='${MESSAGE_ID}';" \
      2>/dev/null || echo 0
  )
  if [[ "$INBOX_COUNT" != "0" ]]; then
    echo "OK: message reached orchestrator inbox"
    break
  fi
  sleep 2
done
test "$INBOX_COUNT" != "0"

curl --fail --silent --show-error http://localhost:9405/clients/11111111111/card/limit \
  | tee "$ARTIFACT_DIR/card-limit.json"
curl --fail --silent --show-error http://localhost:9401/clients/11111111111 \
  | tee "$ARTIFACT_DIR/client.json"

"${COMPOSE[@]}" exec -T postgres psql -U postgres -d conversational_ai -P pager=off \
  -c "select tenant_id, message_id, status, completion_reason, attempt_count, last_error from ops.message_inbox order by received_at desc limit 20;" \
  >"$ARTIFACT_DIR/message-inbox.txt"

"${COMPOSE[@]}" exec -T postgres psql -U postgres -d conversational_ai -P pager=off \
  -c "select tenant_id, conversation_id, journey_version, effect_type, status, attempt_count, next_attempt_at, last_error from ops.orchestrator_outbox order by created_at desc limit 50;" \
  >"$ARTIFACT_DIR/orchestrator-outbox.txt"

"${COMPOSE[@]}" exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list \
  >"$ARTIFACT_DIR/kafka-topics.txt"

curl --fail --silent --show-error http://localhost:9090/api/v1/alerts >"$ARTIFACT_DIR/prometheus-alerts.json"
curl --fail --silent --show-error http://localhost:9090/api/v1/targets >"$ARTIFACT_DIR/prometheus-targets.json"

if [[ "${RUN_LOAD_TEST:-true}" == "true" ]]; then
  docker run --rm --network host \
    -e BASE_URL=http://localhost:5153 \
    -v "$ARCH_ROOT/tests/load:/tests:ro" \
    grafana/k6:2.0.0 run /tests/readiness.js \
    | tee "$ARTIFACT_DIR/k6-readiness.txt"
fi

"${COMPOSE[@]}" ps >"$ARTIFACT_DIR/compose-ps.txt"
popd >/dev/null
echo "OK: multi-repository E2E completed"
