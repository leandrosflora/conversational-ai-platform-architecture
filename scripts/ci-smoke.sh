#!/usr/bin/env bash
set -Eeuo pipefail

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.override.yml)
INFRA_SERVICES=(redis mongodb postgres opensearch kafka kafka-init jaeger loki alloy prometheus grafana)

cleanup() {
  local exit_code=$?
  if (( exit_code != 0 )); then
    echo "::group::Docker Compose diagnostics"
    "${COMPOSE[@]}" ps || true
    "${COMPOSE[@]}" logs --no-color --tail=200 "${INFRA_SERVICES[@]}" || true
    echo "::endgroup::"
  fi
  "${COMPOSE[@]}" down -v --remove-orphans || true
  exit "$exit_code"
}
trap cleanup EXIT

wait_http() {
  local name=$1
  local url=$2
  local attempts=${3:-90}
  for ((i = 1; i <= attempts; i++)); do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null; then
      echo "OK: $name ($url)"
      return 0
    fi
    sleep 2
  done
  echo "ERROR: timeout waiting for $name ($url)" >&2
  return 1
}

assert_topic() {
  local topic=$1
  grep -Fxq "$topic" <<<"$KAFKA_TOPICS" || {
    echo "ERROR: Kafka topic not found: $topic" >&2
    return 1
  }
  echo "OK: Kafka topic $topic"
}

"${COMPOSE[@]}" config --quiet
"${COMPOSE[@]}" up -d "${INFRA_SERVICES[@]}"

wait_http "OpenSearch" "http://localhost:9200/_cluster/health"
wait_http "Jaeger" "http://localhost:16686/"
wait_http "Loki" "http://localhost:3100/ready"
wait_http "Grafana Alloy" "http://localhost:12345/-/ready"
wait_http "Prometheus" "http://localhost:9090/-/ready"
wait_http "Grafana" "http://localhost:3001/api/health"

KAFKA_TOPICS=$("${COMPOSE[@]}" exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list)
for topic in channel.message.received channel.message.status channel.webhook.received channel.webhook.received.retry channel.webhook.received.dlq intent.detected conversation.state_changed agent.events tool.executed; do
  assert_topic "$topic"
done

curl --fail --silent --show-error "http://localhost:9090/api/v1/targets" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
targets = payload["data"]["activeTargets"]
alloy = [t for t in targets if t.get("labels", {}).get("job") == "alloy"]
if not alloy:
    raise SystemExit("Prometheus target alloy not found")
if not any(t.get("health") == "up" for t in alloy):
    raise SystemExit("Prometheus target alloy is not UP")
print("OK: Prometheus scrapes Grafana Alloy")
'

for datasource in prometheus loki jaeger; do
  curl --fail --silent --show-error --user admin:admin "http://localhost:3001/api/datasources/uid/$datasource" >/dev/null
done

echo "OK: Grafana datasources provisioned"
"${COMPOSE[@]}" ps
