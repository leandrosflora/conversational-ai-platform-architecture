# conversation-audit-service

Repo: [`leandrosflora/conversation-audit-service`](https://github.com/leandrosflora/conversation-audit-service) · Stack: .NET 8, Minimal API, Npgsql · Local/host port: `8300`

## Primary responsibility

The platform's real Audit Service: it receives one journey event per processed message and writes a durable row to PostgreSQL. It replaces the removed `audit-service-mock` and is already called by `conversation-orchestrator` at the end of every `IngestMessageUseCase.ExecuteAsync` execution.

## Data owned by the service

It has no domain model of its own beyond the input DTO (`JourneyAuditEvent`: `ConversationId`, `Intent?`, `Outcome`, `Timestamp`) — all persisted state lives in the generic `ops.audit_events` table, which is provisioned to support any platform audit event, not only conversation journeys. The `idempotency_key` column stores the request idempotency header and supports deduplication (see "Business rules").

## Published APIs

| Method | Route | Description |
|---|---|---|
| `POST` | `/journey-events` | Receives `{ conversationId, intent?, outcome, timestamp }` and writes a row to `ops.audit_events` before responding |

Requires `Authorization: Bearer <internal JWT>`, `X-Tenant-Id` matching the signed `tenant_id` claim, and an `Idempotency-Key` header.

Validation: `401` without a valid JWT; `403` if `X-Tenant-Id` does not match the signed claim; `400 Bad Request` when `Idempotency-Key`, `conversationId`, `outcome`, or `timestamp` is missing. Success: `202 Accepted` with no body only after the PostgreSQL write is confirmed. Returns `503 Service Unavailable` when PostgreSQL is unreachable — never a hang or raw `500`.

## Published events

None. The service does not use Kafka.

## Consumed events

None.

## Synchronous dependencies

No HTTP calls to another service — the only dependency is PostgreSQL (see Persistence).

## Persistence and infrastructure

- **PostgreSQL** (`ops.audit_events`) — the service's only storage, accessed directly through `Npgsql` without an ORM. `NpgsqlDataSource` is a singleton with `Timeout=5s`/`CommandTimeout=5s` forced in the connection string so a real PostgreSQL outage becomes a fast `503` instead of the much longer Npgsql defaults (15s connection / 30s command).
- Field mapping (`ops.audit_events` is a generic audit table, not conversation-specific):
  - `tenant_id` = resolved from the request (signed `tenant_id` claim / `X-Tenant-Id`), no longer a fixed seed.
  - `idempotency_key` = the request `Idempotency-Key` header.
  - `actor_type` = `"system"`, `actor_id` = `"conversation-orchestrator"`, `action` = `"conversation.journey_processed"`, `resource_type` = `"conversation"`.
  - `resource_id` = the received `conversationId`.
  - `payload` (jsonb) = `{"intent": ..., "outcome": ...}` — `intent` may be `null`.
  - `created_at` = the timestamp received in the request, not server-side `now()` — it reflects when the Orchestrator observed the outcome rather than when this HTTP request arrived.

## Business rules

1. **Deduplicated by `(tenant_id, idempotency_key)`**: the insert uses `ON CONFLICT (tenant_id, idempotency_key) DO NOTHING`, backed by the migrated unique index `ux_audit_events_tenant_idempotency_key`. A network retry from the Orchestrator using the same `Idempotency-Key` does not create a second row — unlike an older version of this document, which described the audit trail as intentionally non-deduplicated.
2. `created_at` is always the timestamp supplied by the caller and is never recalculated by the server, preserving when the event actually occurred from the Orchestrator's perspective.
3. PostgreSQL unavailability never becomes a generic `500` or blocks indefinitely — it always returns `503` within the configured 5-second timeout.

## Architecture references

- [ADR 0002 — Hexagonal / ports-and-adapters in .NET services](../adr/0002-hexagonal-ports-and-adapters.md)
- [ADR 0004 — Catch-log-continue resilience](../adr/0004-catch-log-continue-resilience.md)
- [conversation-orchestrator](conversation-orchestrator.md) — caller of this service
- [Contracts — Datastores](../contracts/data-stores.md)
