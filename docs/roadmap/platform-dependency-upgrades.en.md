# Kafka, Jaeger, and Loki Upgrade Plan

## Objective

Move away from archived or old versions without combining upgrades of three critical components in the same change set. Each stage must preserve the local environment, CI smoke test, and E2E journey evidence.

## Baseline

| Component | Current version | Target line | Priority | Reason |
|---|---:|---:|---|---|
| Kafka | `3.9.2` | `4.3.x` | High | The 3.9 line is archived; migration requires client and KRaft configuration validation |
| Jaeger | `1.60` all-in-one | `2.x` | High | The 1.x line is archived and the Jaeger 2 configuration model changed |
| Loki | `2.9.8` | `3.7.x` | High | The 3.x line is current and must be validated with TSDB schema and Grafana Alloy |
| Grafana Alloy | `1.16.1` | Controlled continuous upgrades | Medium | Replaces Promtail and becomes the default collector |

## Strategy

### Phase 0 — Baseline and protection

- Keep `scripts/ci-smoke.sh` green.
- Record startup time, memory usage, and health endpoints.
- Confirm the nine Kafka topics, Loki labels, Jaeger datasource, and Alloy target in Prometheus.
- Preserve local volumes before any destructive test.

**Exit:** reproducible baseline and documented rollback.

### Phase 1 — Loki 2.9.8 → 3.7.x

1. Update only the Loki image.
2. Validate `schema_config` v13 and local TSDB storage.
3. Confirm ingestion through Alloy and queries by `{service="..."}`.
4. Run the smoke test and one E2E journey.
5. Validate dashboards and retention before removing the old volume.

**Rollback:** restore the previous image and the volume captured before migration.

### Phase 2 — Jaeger 1.60 → 2.x

1. Create an explicit configuration file for Jaeger 2.
2. Migrate from `jaegertracing/all-in-one` to `jaegertracing/jaeger`.
3. Preserve OTLP gRPC `4317`, OTLP HTTP `4318`, and UI `16686`.
4. Adjust the metrics endpoint used by Prometheus.
5. Confirm traces from .NET and Python services and the Grafana datasource.

**Rollback:** return to all-in-one 1.x while the 2.x configuration format is under homologation.

### Phase 3 — Kafka 3.9.2 → 4.3.x

1. Inventory client-library versions across all repositories.
2. Run producer/consumer compatibility tests before changing the broker.
3. Review removed, changed, or deprecated KRaft settings.
4. Update `kafka` and `kafka-init` together.
5. Validate creation of all nine topics, retry, DLQ, offset commits, and Inbox/Outbox behavior.
6. Execute the E2E journey with an induced Orchestrator failure to confirm retry and redelivery.

**Rollback:** restore the broker image and volume; do not reuse a converted volume without downgrade testing.

## Acceptance criteria per phase

- `docker compose config --quiet` completes without error.
- `mkdocs build --strict` has no invalid links.
- `scripts/ci-smoke.sh` is green.
- No topic, port, or datasource is removed without a documented replacement.
- The main E2E journey completes.
- Evidence is added under `docs/validation/`.
- Rollback is executed at least once in a disposable environment.

## Recommended order

```text
Alloy (completed)
  → Loki
  → Jaeger
  → Kafka
```

Loki comes first because it already receives logs through Alloy. Jaeger comes next because it requires a larger configuration change. Kafka remains last because it affects durability, retry, DLQ, and the critical ingress path.
