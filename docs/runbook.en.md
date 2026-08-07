# Runbook — Conversational AI Platform

## 1. Scope

This runbook describes the coordinated `main` state of `conversational-ai-platform-architecture` and the service repositories. The solution is an executable/hardened POC reference, not banking production-ready.

## 2. Workspace

```text
workspace/
├── conversational-ai-platform-architecture/
├── whatsapp-bff/
├── conversation-orchestrator/
├── agent-runtime-renegotiation/
├── tool-service-renegotiation/
├── renegotiation-service/
├── agent-runtime-fatura-cartao/
├── tool-service-cartao-credito/
├── knowledge-service/
├── conversation-memory-service/
├── conversation-audit-service/
├── conversation-handoff-service/
└── core-bancario-mock/
```

Changes to authentication, tenant handling, contracts, or journey state require coordinated deployment and validation.

## 3. Configuration

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Each issuer/audience pair has an independent secret. Integrated Compose also enables authentication in `core-bancario-mock`, with distinct pairs for:

```text
renegotiation-service → core-bancario-mock
tool-service-cartao-credito → core-bancario-mock
```

Never commit real values.

## 4. CI

CI in this repository validates:

- Compose and contracts;
- Alloy, Prometheus, and Alertmanager;
- scripts and canonical documentation;
- C4, MkDocs, and links;
- Trivy, SARIF, and SBOM;
- real infrastructure smoke testing.

`core-bancario-mock` runs restore, build, and integration tests for authentication, health, and idempotency. The remaining services maintain their own pipelines.

## 5. Local startup

```bash
scripts/write-ci-env.sh
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.override.yml ps
```

## 6. Ports

| Service | Host port | Signal |
|---|---:|---|
| whatsapp-bff | `5153` | `/health/ready` |
| conversation-orchestrator | `5268` | `/health/ready` |
| agent-runtime-renegotiation | `8100` | `/health/ready` |
| agent-runtime-fatura-cartao | `8110` | `/health/ready` |
| conversation-handoff-service | `8200` | `/health/ready` |
| conversation-audit-service | `8300` | `/health/ready` |
| tool-service-renegotiation REST | `8401` | `/health/ready` |
| tool-service-cartao-credito REST | `8411` | `/health/ready` |
| knowledge-service | `8500` | `/health/ready` |
| conversation-memory-service | `8600` | `/health/ready` |
| renegotiation-service | `5266` | `/health/ready` |
| core-bancario-mock | `9401`–`9405` | `/health/ready` |
| Kafka UI | `8080` | UI |
| Jaeger | `16686` | UI |
| Prometheus | `9090` | UI/API |
| Alertmanager | `9093` | UI/API |
| Grafana | `3001` | UI |
| Alloy | `12345` | `/-/ready` |

## 7. Authentication

Internal calls use:

```text
Authorization: Bearer <JWT>
X-Tenant-Id: <UUID>
```

Common claims:

```text
iss, sub, aud, iat, exp, jti, tenant_id, kid
```

Expected outcomes:

- missing/invalid token: `401`;
- missing or invalid tenant: `400`;
- tenant mismatch or unauthorized caller: `403`.

The Core accepts `renegotiation-service` on renegotiation APIs and `tool-service-cartao-credito` only on the Card API. Health and metrics remain public.

## 8. Persistence and consistency

PostgreSQL:

```text
ops.message_inbox
ops.conversation_state
ops.orchestrator_outbox
ops.renegotiation_idempotency
ops.audit_events
conversation.handoffs
```

MongoDB:

```text
conversation_messages
unique partial index: (tenantId, externalMessageId)
```

OpenSearch:

```text
faq_chunks-<tenant-uuid>
```

The Orchestrator's `202` confirms that state and effects have been recorded, not that all downstream systems have completed processing.

The Core requires `Idempotency-Key` for simulation/confirmation and maintains replay/conflict in memory. The primary durability guarantee remains PostgreSQL in Renegotiation Service.

## 9. Kafka

```text
channel.webhook.received
channel.webhook.received.retry
channel.webhook.received.dlq
```

The original offset is committed only after processing or confirmed publication to retry/DLQ.

## 10. Observability

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d \
  jaeger loki alloy alertmanager prometheus grafana
```

Prometheus loads rules from `config/prometheus/rules/`. Local Alertmanager uses a null receiver. See:

- [SLOs and alerts](operations/slo-alerting.md)
- `http://localhost:9090/alerts`
- `http://localhost:9093`
- `http://localhost:3001`

## 11. Multi-repository E2E

```bash
scripts/e2e-multirepo.sh
```

The script:

1. records commits for all 12 services;
2. runs builds and tests;
3. starts the complete stack;
4. validates readiness;
5. sends a signed Meta webhook;
6. verifies Inbox/Outbox;
7. issues temporary JWTs to test the Core;
8. validates caller, tenant, replay, and idempotent conflict;
9. collects Kafka/Prometheus/evidence;
10. runs the k6 baseline.

In GitHub Actions, configure `MULTIREPO_READ_TOKEN` with read access to all 12 repositories. For manual execution, `core_ref` allows validating the coordinated Core branch before merge.

## 12. Backup and restore

```bash
scripts/backup-local.sh
```

```bash
ALLOW_DESTRUCTIVE_RESTORE=true \
  scripts/restore-local.sh backups/<timestamp>
```

See [Backup, restore, and recovery](operations/disaster-recovery.md).

## 13. Load and chaos

```bash
docker run --rm --network host \
  -e BASE_URL=http://localhost:5153 \
  -v "$PWD/tests/load:/tests:ro" \
  grafana/k6:2.0.0 run /tests/readiness.js
```

```bash
ALLOW_DESTRUCTIVE_DRILL=true \
  scripts/chaos-drill.sh conversation-memory-service
```

See [Load and chaos testing](testing/load-and-chaos.md).

## 14. LGPD

The initial technical matrix is documented in [Retention, classification, and LGPD](governance/data-retention-lgpd.md). Retention periods require Legal/Privacy/Business approval.

## 15. Reset

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml down
```

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml down -v
```

## 16. Limitations

- Core idempotency is process-local;
- per-pair HS256 has no rotation/JWKS;
- Handoff does not integrate with a real human-service platform;
- Alertmanager receiver is local/null;
- Kafka, OpenSearch, and network use local configuration;
- image signing/attestation is not uniform across services;
- managed retention, deletion, and encryption depend on enterprise implementation;
- Kafka/OpenSearch restore is based on rebuild/replay;
- multi-repository E2E depends on `MULTIREPO_READ_TOKEN`.

## 17. Troubleshooting

### Compose requires a secret

Run `scripts/write-ci-env.sh` or populate every pair from `.env.example`.

### Core returns `503` on readiness

Authentication is enabled and one inbound secret is missing or shorter than 32 bytes.

### Core returns `401`/`403`

Check `kid`, `sub`, audience `core-bancario-mock`, the pair-specific secret, and equality between `tenant_id` and `X-Tenant-Id`.

### Core operation returns `400`

Simulation and confirmation require `Idempotency-Key`.

### Prometheus rule does not load

```bash
docker run --rm --entrypoint /bin/promtool \
  -v "$PWD/config/prometheus:/etc/prometheus:ro" \
  prom/prometheus:v2.53.1 \
  check config /etc/prometheus/prometheus.yml
```
