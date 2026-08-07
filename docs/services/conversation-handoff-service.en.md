# conversation-handoff-service

Repo: [`leandrosflora/conversation-handoff-service`](https://github.com/leandrosflora/conversation-handoff-service) · Stack: .NET 8, Minimal API, Npgsql · Local/host port: `8200`

## Primary responsibility

The platform's real Handoff Service: it receives a request to transfer a conversation to human support and writes a durable row to PostgreSQL. Unlike the Audit Service, the `conversation-orchestrator` call to this service **was never commented out** — whenever the Agent Runtime recommends or requires handoff (`RequiresHandoff=true`), the Orchestrator has always called this host unconditionally; what was missing was a real service on the other side.

## Data owned by the service

It has no domain model of its own beyond the input DTO (`HandoffRequestRecord`: `ConversationId`, `Reason`) — all persisted state lives in the `conversation.handoffs` table, already provisioned in the `conversation` schema. The `idempotency_key` column stores the request idempotency header.

## Published APIs

| Method | Route | Description |
|---|---|---|
| `POST` | `/handoffs` | Receives `{ conversationId, reason }` and writes a row to `conversation.handoffs` before responding |

Requires `Authorization: Bearer <internal JWT>`, `X-Tenant-Id` matching the signed `tenant_id` claim, and an `Idempotency-Key` header.

Validation: `401` without a valid JWT; `403` if `X-Tenant-Id` does not match the signed claim; `400 Bad Request` if `Idempotency-Key`, `conversationId`, or `reason` is missing. Success: `202 Accepted` with no body only after the PostgreSQL write is confirmed. Returns `503 Service Unavailable` if PostgreSQL is unreachable — never a hang or raw `500`.

## Published events

None. The service does not use Kafka.

## Consumed events

None.

## Synchronous dependencies

No HTTP calls to another service — the only dependency is PostgreSQL (see Persistence). There is no real step that transfers the case to a human operator (the `handoffService → attendance` relationship in the C4 model is conceptual): this service accepts and persists the request, the same scope boundary used by `conversation-audit-service` with respect to the Data Lake.

## Persistence and infrastructure

- **PostgreSQL** (`conversation.handoffs`) — the service's only storage, accessed directly through `Npgsql` without an ORM, following the same pattern as `conversation-audit-service` (`NpgsqlDataSource` singleton with forced `Timeout=5s`/`CommandTimeout=5s`).
- Each row now also stores `tenant_id` directly (column added after the original table) — but the **foreign key on `conversation.handoffs.conversation_id`** still requires an existing row in `conversation.conversations`, a table that no service in this workspace actually populates (there is no phone → conversation UUID resolution anywhere). Every row therefore continues to use the provisioned seed conversation (`70000000-0000-0000-0000-000000000001`) as a fixed FK; the real conversation ID (phone number) is stored in `metadata.externalConversationId`/`metadata.tenantId` so it is not lost.
- `target_queue` is always the literal `"human-support"` — this workspace does not yet implement skill-based queue/routing concepts.
- `status` remains at the table default (`"pending"`) — there is no implemented flow for accepting/closing a handoff (`accepted_at`/`closed_at` exist in the schema but nothing writes them).

## Business rules

1. Every handoff row points to the same seed conversation through the FK — two different real conversations are distinguished by the `tenant_id` column and `metadata.externalConversationId`, never by `conversation_id`. This is acceptable because no operator tool queries `conversation.handoffs` yet.
2. **Deduplicated by `(tenant_id, idempotency_key)`**: the insert uses `ON CONFLICT (tenant_id, idempotency_key) DO NOTHING`, backed by the migrated unique index `ux_handoffs_tenant_idempotency_key`. A network retry from the Orchestrator using the same `Idempotency-Key` does not create a second row.
3. PostgreSQL unavailability never becomes a generic `500` or blocks indefinitely — it always returns `503` within the configured 5-second timeout.

## Architecture references

- [ADR 0002 — Hexagonal / ports-and-adapters in .NET services](../adr/0002-hexagonal-ports-and-adapters.md)
- [ADR 0004 — Catch-log-continue resilience](../adr/0004-catch-log-continue-resilience.md)
- [conversation-orchestrator](conversation-orchestrator.md) — caller of this service
- [Contracts — Datastores](../contracts/data-stores.md)
