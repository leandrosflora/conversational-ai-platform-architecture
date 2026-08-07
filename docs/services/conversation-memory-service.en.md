# conversation-memory-service

Repo: [`leandrosflora/conversation-memory-service`](https://github.com/leandrosflora/conversation-memory-service) · Stack: Python, FastAPI, Redis, MongoDB · Local port: `8600`

## Primary responsibility

Platform memory: active conversation session in Redis with TTL and durable memory in MongoDB — message history and long-term memory facts per user. It is already consumed by two real clients: `conversation-orchestrator` for session state and message-history writes on every processed message, and `agent-runtime-renegotiation`, which reads recent history before invoking the agent. Long-term memory facts (`agent_memory`) still have no real reader or writer — no service in this workspace decides what becomes a "fact" or has a `user_id` to address it.

## Data owned by the service

- **Active session** (Redis key `tenant:{tenant_id}:session:{conversation_id}`): opaque JSON payload (`data`, fully defined by the caller) plus `updated_at`, with TTL (default `session_ttl_seconds=1800`, the same TTL the Orchestrator used for its in-memory session before this integration).
- **Message history** (MongoDB `conversation_messages`): `tenantId`, `conversationId`, `userId`, `channel`, `provider`, `externalMessageId`, `role`, `content`, `metadata`, `correlationId`, `traceId`, `createdAt`.
- **Long-term memory** (MongoDB `agent_memory`): one document per `(tenantId, userId, memoryType)` with `facts[]`, `sourceConversationId`, `createdAt`/`updatedAt`, and optional `expiresAt`.

## Published APIs

| Method | Route | Description |
|---|---|---|
| `GET` | `/sessions/{conversation_id}` | Active session; `404` if it does not exist or has expired |
| `PUT` | `/sessions/{conversation_id}` | Creates or replaces the session; default TTL or explicit `ttl_seconds` in the body |
| `DELETE` | `/sessions/{conversation_id}` | Removes the session; returns `204` even if already absent (idempotent) |
| `POST` | `/conversations/{conversation_id}/messages` | Appends a message to history; `201` if created, `200` if it already existed (idempotent; see Business rules) |
| `GET` | `/conversations/{conversation_id}/messages` | Lists history filtered by `tenant_id`, with optional `limit`, newest records selected and returned chronologically |
| `GET` | `/users/{user_id}/memory` | Memory facts for `tenant_id`/`memory_type`; returns an empty list if none exist |
| `PUT` | `/users/{user_id}/memory` | Replaces the entire `facts[]` array by upsert; optional `ttl_seconds` recalculates `expiresAt` |

Every endpoint returns `503 Service Unavailable` when Redis or MongoDB are unavailable (`DatastoreUnavailableError`, mapped by a central exception handler in `app/main.py`) — never a hang or raw `500`.

## Published events

None.

## Consumed events

None.

## Synchronous dependencies

| Destination | Behavior when unavailable |
|---|---|
| Redis (`:6379`) | Client uses `socket_connect_timeout=3s`/`socket_timeout=3s`; without this, the much longer `redis-py` timeout would leave the call hanging before `503` is returned |
| MongoDB (`:27017` internal / `:27018` host) | Driver errors (`PyMongoError`) become `DatastoreUnavailableError` → `503` for all session/history/memory operations |

## Persistence and infrastructure

- **Redis**: active session by conversation with TTL — the only source of truth for the conversation's "hot" state.
- **MongoDB**: message history (`conversation_messages`) and long-term memory (`agent_memory`), using the schema/indexes provisioned in `database/conversational-ai-mongodb-init.js` and the least-privilege application user (`conversational_ai_app`, `readWrite`) — never the root user.
- On startup, `ensure_indexes` does more than mirror the Mongo initialization script: it **actively migrates** a legacy globally unique `externalMessageId_1` index (still defined in `database/conversational-ai-mongodb-init.js`, from before multitenancy) to the tenant-scoped composite index `ux_conversation_messages_tenant_external_message` on `(tenantId, externalMessageId)`, which is the real idempotency key today. This covers both pre-existing Mongo volumes that never ran the init script and volumes initialized with its older version.

## Business rules

1. **History is idempotent by `externalMessageId`**: if a document already exists with the same `(tenantId, externalMessageId)`, append is treated as a retry and returns the existing document with `200 OK` instead of duplicating it or raising a unique-key error. A race between two concurrent appends using the same `externalMessageId` is resolved by reading the winning document after `DuplicateKeyError`.
2. **Long-term memory is full replacement, not merge**: `PUT /users/{id}/memory` replaces the entire `facts[]` array for that `(tenantId, userId, memoryType)` and does not merge fact by fact. This can lose updates if two callers concurrently write different facts for the same user; acceptable today because only one caller is expected (Agent Runtime), and no service currently calls this endpoint in practice.
3. **Memory expiration is evaluated at read time, not only by Mongo's TTL index**: Mongo TTL deletion runs periodically rather than instantly, so a document can be logically expired before physical deletion. `GET /users/{id}/memory` treats past `expiresAt` values as absent regardless of whether the document still physically exists.
4. Session `data` is an opaque JSON payload — the service imposes no schema because the caller (`conversation-orchestrator`) fully defines what is stored there.

## Architecture references

- [ADR 0002 — Hexagonal / ports-and-adapters in .NET services](../adr/0002-hexagonal-ports-and-adapters.md) — this service is Python, but its client in `conversation-orchestrator` follows the convention through `IConversationMemoryClient`.
- [Journey sequence diagrams](../architecture/sequence-diagrams.md)
- [Contracts — Datastores](../contracts/data-stores.md)
