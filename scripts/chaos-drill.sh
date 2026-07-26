#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${ALLOW_DESTRUCTIVE_DRILL:-false}" != "true" ]]; then
  echo "ERROR: drill bloqueado. Execute com ALLOW_DESTRUCTIVE_DRILL=true." >&2
  exit 2
fi

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.override.yml")
SERVICE=${1:-conversation-memory-service}
PAUSE_SECONDS=${PAUSE_SECONDS:-20}

case "$SERVICE" in
  conversation-memory-service|conversation-audit-service|conversation-handoff-service|renegotiation-service|knowledge-service)
    ;;
  *)
    echo "ERROR: serviço não permitido para este drill: $SERVICE" >&2
    exit 2
    ;;
esac

cleanup() {
  "${COMPOSE[@]}" unpause "$SERVICE" >/dev/null 2>&1 || true
}
trap cleanup EXIT

"${COMPOSE[@]}" ps "$SERVICE"
"${COMPOSE[@]}" pause "$SERVICE"
echo "Serviço $SERVICE pausado por ${PAUSE_SECONDS}s."
sleep "$PAUSE_SECONDS"
"${COMPOSE[@]}" unpause "$SERVICE"

for ((i=1; i<=60; i++)); do
  STATUS=$("${COMPOSE[@]}" ps --format json "$SERVICE" 2>/dev/null || true)
  if grep -q '"State":"running"' <<<"$STATUS"; then
    echo "OK: $SERVICE voltou ao estado running"
    exit 0
  fi
  sleep 2
done

echo "ERROR: $SERVICE não recuperou após o drill" >&2
exit 1
