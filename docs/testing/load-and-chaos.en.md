# Load and Chaos Testing

## Load

`tests/load/readiness.js` uses k6 with a constant request rate and explicit thresholds:

```bash
docker run --rm --network host \
  -e BASE_URL=http://localhost:5153 \
  -v "$PWD/tests/load:/tests:ro" \
  grafana/k6:2.0.0 run /tests/readiness.js
```

Baseline:

- 10 requests per second for 30 seconds;
- less than 1% failures;
- `p95` below 500 ms;
- more than 99% of checks passing.

The readiness test validates basic capacity. Production requires webhook, Orchestrator, RAG, and tool scenarios with synthetic data and per-tenant limits.

## Controlled chaos

`scripts/chaos-drill.sh` temporarily pauses only allowlisted services and restores the container when it exits.

```bash
ALLOW_DESTRUCTIVE_DRILL=true \
  PAUSE_SECONDS=20 \
  scripts/chaos-drill.sh conversation-memory-service
```

Do not run this against shared environments or production.

## Recommended scenarios

- Memory, Audit, or Handoff unavailable during Outbox publishing;
- Renegotiation Service unavailable during simulation;
- OpenSearch slow or unavailable;
- Orchestrator restart with an active lease;
- temporary Kafka outage;
- model-provider error/timeout;
- downstream recovery and replay without duplication.

## Acceptance criteria

- no accepted message is lost;
- Outbox/Retry/DLQ reflect the failure;
- later versions do not overtake earlier effects;
- recovery does not duplicate side effects;
- corresponding alerts become visible;
- the report includes timestamps, commits, logs, and datastore state.
