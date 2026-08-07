# conversation-orchestrator

Repo: [`leandrosflora/conversation-orchestrator`](https://github.com/leandrosflora/conversation-orchestrator) · Stack: .NET 8, Minimal API, PostgreSQL, Confluent.Kafka · Local port (`dotnet run`): `8000` · Host port through `docker compose up -d`: `5268` (see [`runbook.md`](../runbook.md))

## Primary responsibility

Receives an inbound message already normalized by `whatsapp-bff` at `POST /messages` and admits it idempotently and in order through a transactional PostgreSQL Inbox. Within the same admission transaction, it calls the AI agent for the conversation's active skill (routing between `agent-runtime-renegotiation` and `agent-runtime-fatura-cartao` through a tenant-configurable `AgentSkillRegistry`), determines the next `journey_stage` (an opaque string owned by the skill, not by the Orchestrator), and writes the turn's side effects — channel response, memory projection, audit, handoff, and Kafka events — into a durable Outbox, all within the same PostgreSQL transaction. The endpoint returns `202`/`409` without waiting for any of those effects to be delivered. A background `OutboxDispatcherService` publishes them later, in order, with retry and backoff. This is the most important architectural change from older versions of the service: the pipeline is no longer synchronous end to end.

## Data owned by the service

The Orchestrator persists directly to PostgreSQL under schema `ops`, unlike older versions where it had no database of its own:

- `ops.message_inbox` — admission/deduplication ledger by `(tenant_id, message_id)`: `status` (`processing`/`completed`/`failed`), `lease_until`, `attempt_count`, `completion_reason`, `source_received_at`.
- `ops.conversation_state` — current conversation state: `journey_stage` (**opaque string**, owned by the active skill rather than a closed Orchestrator enum), `version`, `skill_id`, `structured_state` (opaque jsonb), `last_intent`, `last_received_at`/`last_message_id` for late-message detection, `processing_message_id`/`processing_lease_until` for the conversation lease, and `session_started_at`. Renegotiation-specific columns from an older version (`active_contract_id`, `active_simulation_id`, `active_agreement_id`) were removed; the current design is deliberately skill-agnostic.
- `ops.orchestrator_outbox` — queue of pending effects per turn: `effect_type`, `journey_version`, `idempotency_key`, `payload` (jsonb), `status` (`pending`/`publishing`/`published`/`failed`), `attempt_count`, `next_attempt_at`, `locked_until`.

## Published APIs

| Method | Route | Description |
|---|---|---|
| `POST` | `/messages` | Admits a normalized inbound message and returns before any side effect is delivered |

Requires `Authorization: Bearer <internal JWT>` and `X-Tenant-Id` matching the signed `tenant_id` claim.

- `400 Bad Request` — empty `MessageId`/`From`/`ConversationId` or default `ReceivedAt`.
- `401` — missing/invalid/expired JWT through the standard `JwtBearer` pipeline.
- `403 Forbidden` — `X-Tenant-Id` is not a UUID or does not match the JWT `tenant_id` claim.
- `202 Accepted`, empty body — both a normally admitted turn **and** an already completed/late message (`AlreadyCompleted`/late message), intentionally indistinguishable to the caller.
- `409 Conflict` — message or conversation is already under an active processing lease; response: `{"error": "Message or conversation is already being processed. Retry after the active lease completes."}`.
- An unhandled exception, such as an optimistic-version guard failure in `CompleteAsync`, propagates as `500`; `whatsapp-bff` treats it as failure and redelivers through its retry/DLQ mechanism.

## Published events

| Topic | When | Payload |
|---|---|---|
| `intent.detected` | When the agent returns a non-empty `Intent` | `ConversationId`, `Intent`, `Confidence`, `DetectedAt` |
| `conversation.state_changed` | When `journey_stage` changes from its previous value | `ConversationId`, `PreviousStage`, `NewStage`, `ChangedAt` |

Unlike older versions, these events are **not** published synchronously inside the request. They are Outbox effects (`kafka.intent_detected`, `kafka.state_changed`) dispatched later by `OutboxDispatcherService`. Kafka publication failure is no longer swallowed and forgotten; it follows normal Outbox retry/backoff until publication succeeds or the effect is parked.

## Consumed events

None. There is no `IConsumer` in the process. `OutboxDispatcherService` is a `BackgroundService` that polls PostgreSQL using `FOR UPDATE SKIP LOCKED` plus an in-process semaphore signaled on every admission; it is not a Kafka consumer.

## Synchronous dependencies

| Destination | Call | Timeout/retry | Behavior when unavailable |
|---|---|---|---|
| `agent-runtime-renegotiation` (skill `renegotiation`, `:8100`) and `agent-runtime-fatura-cartao` (skill `cartao-credito`, `:8110`) | `POST /process`, one named HTTP client per skill with identical configuration | `AttemptTimeout=45s`, `TotalRequestTimeout=60s`, `CircuitBreaker.SamplingDuration=90s`, 2 retries/200ms | Never throws to the caller — degrades to `AgentRuntimeResult.Unavailable()`, forcing `RequiresHandoff=true`, `HandoffReason="agent_runtime_unavailable"`. This call remains synchronous inside the request because the turn cannot be decided without the agent |
| `whatsapp-bff` (`:5153`) | `POST /internal/messages` as Outbox effect `channel.reply`/`channel.menu` | Default 10s/30s, 2 retries/200ms | A `{"retryable": false}` response causes `NonRetryableDispatchException` and immediate parking/dead-letter; any other failure follows normal Outbox backoff |
| `conversation-handoff-service` (`:8200`) | `POST /handoffs` as Outbox effect `handoff.request` | Default 10s/30s, 2 retries/200ms | Exception propagates to dispatcher → Outbox retry/backoff |
| `conversation-audit-service` (`:8300`) | `POST /journey-events` as Outbox effect `audit.record` | Default 10s/30s, 2 retries/200ms | Same behavior |
| `conversation-memory-service` (`:8600`) | `POST /conversations/{id}/messages`, `PUT /sessions/{id}` as `memory.append_message`/`memory.save_session` effects | Default 10s/30s, 2 retries/200ms | Same behavior. `GetOrCreateSessionAsync` still exists on the client but is no longer called; conversation state now comes only from the `ops.conversation_state` checkpoint |

All five client families attach a per-pair internal JWT (issuer, audience) through `InternalTokenService`/`InternalRequestHandler`.

**Known gap:** `/health/ready` checks `ExpectedOutboundAudiences` but still lists only `agent-runtime-renegotiation`; it does not include `agent-runtime-fatura-cartao`, so a missing/invalid outbound secret for the second skill is not detected by readiness.

## Persistence and infrastructure

PostgreSQL (`ops.message_inbox`, `ops.conversation_state`, `ops.orchestrator_outbox`) is created/migrated idempotently at startup. `NpgsqlDataSource` is a singleton with fixed 5-second connection/command timeouts. Kafka is output-only through producer/admin client for readiness; there is no consumer. `conversation-memory-service` still stores a durable history/session projection in Redis/MongoDB, but today it is only an Outbox destination, not something synchronously read during the request.

## Business rules

1. **Admission idempotency:** `(tenant_id, message_id)` is unique in `ops.message_inbox`. Redelivery of a `completed` message returns `202` without reprocessing. Outbox effects have a second idempotency key `(tenant_id, idempotency_key)` derived from `{tenantId}:{messageId}` plus an effect-type prefix with `ON CONFLICT DO NOTHING`, so even a `CompleteAsync` retry does not duplicate effects.
2. **Conversation lease:** in addition to per-message deduplication, `ops.conversation_state` holds a processing lease per `(tenant_id, conversation_id)`, so two messages from the same conversation never process concurrently. If a second message arrives under an active lease, its newly acquired Inbox row becomes `failed` and reclaimable on retry, while the endpoint returns `409`.
3. **Late message:** a message is late when its `(ReceivedAt, MessageId)` tuple is not strictly greater than that of the conversation's last *completed* message. A late message is marked `completed` with `completion_reason=late_message` without invoking the agent or producing effects; the endpoint still returns normal `202`.
4. **Outbox ordering barrier:** effects from a newer `journey_version` cannot be dispatched while an unpublished effect from an earlier version of the same conversation exists, unless the earlier effect has been parked/dead-lettered with `next_attempt_at` pushed beyond one day. This prevents the customer from seeing turn N+1 before turn N, but a genuinely stuck effect that is still retrying can block later turns for up to roughly 20 attempts with exponential backoff capped at 300 seconds per attempt.
5. **Multi-skill routing:** each tenant has enabled skills in `AgentSkillOptions.TenantSkillAssignments`; the default tenant currently has `renegotiation` and `cartao-credito`. With only one skill it is automatically selected without a menu. With two or more, the skill is pinned to the conversation in `conversation_state.skill_id` until (a) the customer selects another menu button, (b) the 15-minute session expires, or (c) the agent returns `OutOfScope=true`, which unpins the skill and shows the menu again. For a single-skill tenant, out-of-scope becomes handoff with reason `out_of_scope_no_alternative_skill`.
6. **Unconfigured skill:** if the pinned/selected skill no longer exists in `AgentSkillOptions.Skills`, or the tenant has no assigned skill, the turn becomes handoff with reason `skill_not_configured`, using the same treatment as an unavailable Agent Runtime.
7. **15-minute session window:** anchored to `SessionStartedAt`, not last activity. On expiration, `journey_stage`/`structured_state` reset to a clean state, the skill is unpinned (reopening the menu for tenants with 2+ skills), and the agent receives `SessionReset=true` so it can explicitly tell the customer rather than silently asking again.
8. **Reserved states known by the Orchestrator:** all other `journey_stage` values are opaque and owned by the skill, but the Orchestrator knows `Started`, `HandoffRequested`, and `AwaitingSkillSelection`. The last two are deliberately **not** passed as `State` to the agent on the next call, fixing a real bug where the skill Tool Service denied all tools because it interpreted `AwaitingSkillSelection` as the skill's own journey stage.
9. **JWT auth on `/messages`:** issuer/audience/signature are validated using a symmetric key selected by `kid` from `InternalAuth:InboundSecrets`, plus an explicit check that `kid == sub` to prevent one service presenting a token signed with another service's key. `X-Tenant-Id` must also match the token's `tenant_id` claim.
10. **Outbound JWT auth:** each call to the five dependency families carries a short-lived HS256 JWT (30–900 seconds, default 300) signed with the specific secret for that issuer/audience pair in `InternalAuth:OutboundSecrets`, rather than one shared secret. For both agent skills, the audience is the downstream service name configured for the skill (`agent-runtime-renegotiation`/`agent-runtime-fatura-cartao`), each with its own secret.

## Architecture references

- [ADR 0002 — Hexagonal / ports-and-adapters in .NET services](../adr/0002-hexagonal-ports-and-adapters.md)
- [ADR 0004 — Catch-log-continue resilience](../adr/0004-catch-log-continue-resilience.md)
- [ADR 0005 — Transactional Outbox, governed tools, and ordering](../adr/0005-transactional-outbox-governed-tools-and-ordering.md)
- [Journey sequence diagrams](../architecture/sequence-diagrams.md)
