# ADR 0005: Transactional Outbox, Governed Execution, and Per-Conversation Ordering

## Status

**Accepted — P0 consistency.**

## Context

The previous implementation had a persistent Inbox and idempotency in some destinations, but still exposed five risks:

1. the Orchestrator completed the Inbox after attempting synchronous side effects even when degradable adapters swallowed failures;
2. the LLM received all tools and the state machine validated transitions only after execution;
3. `X-Tenant-Id` was not cryptographically bound to the JWT;
4. retry through a separate topic could allow a later message in the same conversation to advance before the earlier one;
5. simulation creation had no durable idempotency.

## Decision

### 1. Authoritative state and Outbox

`conversation-orchestrator` maintains in PostgreSQL:

- `ops.message_inbox`, by `(tenant_id, message_id)`;
- `ops.conversation_state`, by `(tenant_id, conversation_id)`;
- `ops.orchestrator_outbox`, by `(tenant_id, idempotency_key)`.

A message completes in one transaction:

1. validate the expected conversation version;
2. update stage, intent, version, and last received event;
3. write all mandatory effects to the Outbox;
4. complete the Inbox with `completion_reason=effects_persisted`.

The HTTP request does not need to wait for downstream systems. The guarantee is that effects were durably recorded before `202` is returned.

### 2. At-least-once delivery with deduplication

A worker uses leases and `FOR UPDATE SKIP LOCKED` to deliver:

- channel response;
- projections to Memory Service;
- audit;
- handoff;
- Kafka intent and state-change events.

Failures leave an effect in `failed` with exponential backoff. Destinations deduplicate:

- channel: Redis by tenant and `Idempotency-Key`;
- memory: `(tenantId, externalMessageId)`;
- Audit/Handoff: `(tenant_id, idempotency_key)`;
- Kafka: idempotent producer, accepting at-least-once semantics at the consumer.

### 3. Per-conversation ordering

`ops.conversation_state` contains a processing lease and optimistic version.

- only one message per conversation executes the Agent Runtime at a time;
- messages whose `(receivedAt, messageId)` is earlier than or equal to the last applied event are marked `late_message` and do not execute the journey;
- every effect carries `journey_version`;
- the dispatcher does not publish effects for a version while an unpublished effect from an earlier version of the same conversation exists.

### 4. Canonical, signed tenant

The single tenant contract is a non-empty UUID in canonical format.

Internal calls carry tenant identity simultaneously in:

- JWT claim `tenant_id`;
- header `X-Tenant-Id`.

The destination requires the values to match. Idempotency keys and indexes include the tenant.

Shared HS256 remains a POC limitation. The production design still requires workload identity or asymmetric JWT with distinct keys.

### 5. Tool policy enforcement

The Orchestrator sends immutable context to the Agent Runtime:

- tenant;
- conversation;
- message;
- stage;
- version;
- deterministic evidence of explicit confirmation.

The Agent Runtime signs this context in a `tool_execution` JWT intended for the Tool Service.

The Tool Service:

- validates caller and context;
- applies a per-stage tool allowlist;
- requires explicit confirmation for `confirmar_acordo`;
- generates the operation's deterministic `Idempotency-Key`;
- signs a second `governed_tool` proof for Renegotiation Service.

Renegotiation Service repeats validation before simulation or confirmation. Therefore, an LLM instruction alone is insufficient to authorize a transactional operation.

### 6. Simulation idempotency

Renegotiation Service persists:

- tenant;
- operation;
- idempotency key;
- canonical request hash;
- status;
- response;
- error and lease.

Completed repetitions return the persisted response. Reusing the key with a different request returns a conflict.

Because the Banking Core Mock still does not validate idempotency in the state described by this ADR, ambiguous outcomes fail closed: a key in `processing` or `failed` is not automatically reacquired. Administrative reconciliation is required, preventing a potentially duplicated second execution.

## Positive consequences

- a completed Inbox means effects have been durably recorded;
- downstream failures no longer cause silent loss;
- responses, audit, handoff, and memory support replay;
- financial operations no longer depend only on the prompt;
- tenant becomes part of signed identity;
- the journey has explicit version and ordering controls.

## Negative consequences

- more operational states and tables;
- the Outbox requires monitoring, replay, and retention;
- a permanently failed effect blocks later versions of the same conversation until correction or intervention;
- ambiguous simulation outcomes may require manual reconciliation while the Core lacks idempotency;
- PRs must be deployed in a coordinated way because of the new claims and contracts.

## Operations

Minimum alerts:

- growth of Outbox `failed`/`publishing` with expired leases;
- age of the oldest pending effect;
- conversations whose version is blocked by a previous effect;
- denied policy attempts;
- mismatch between signed tenant and header;
- simulation keys in an ambiguous state.

## Completion criterion

P0 is considered integrated only after:

1. build and tests for the nine services;
2. migrations applied in a disposable environment and on an existing volume;
3. E2E with induced channel, Memory, Audit, and Handoff failures;
4. E2E for a late message and two concurrent messages;
5. attempt to confirm an agreement from a forbidden stage;
6. simulation replay using the same key plus conflict with different parameters;
7. isolation validation between two distinct tenant UUIDs.
