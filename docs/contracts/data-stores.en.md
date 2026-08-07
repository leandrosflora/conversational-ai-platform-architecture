# Datastores

**Source of truth:** repository and Compose scan, resynchronized on 2026-07-26.

## Provisioned infrastructure and actual usage

| Datastore | Provisioned? | Implemented consumers |
|---|---|---|
| Kafka | Yes | whatsapp-bff, conversation-orchestrator, agent runtimes, and tool services |
| PostgreSQL | Yes | Orchestrator, Audit, Handoff, and Renegotiation Service |
| MongoDB | Yes | Conversation Memory |
| Redis | Yes | Conversation Memory and whatsapp-bff |
| OpenSearch | Yes | Knowledge Service |

All provisioned datastores have a real consumer.

## By service

| Service | Datastore/state | Details |
|---|---|---|
| whatsapp-bff | Kafka; Redis | ingress/retry/DLQ and outbound deduplication by tenant/key |
| conversation-orchestrator | PostgreSQL; Kafka | Inbox, versioned state, Outbox, and asynchronous events |
| agent-runtime-renegotiation | Kafka | `agent.events`; queries Knowledge |
| tool-service-renegotiation | Kafka | `tool.executed` |
| agent-runtime-fatura-cartao | Kafka | `agent.events` |
| tool-service-cartao-credito | Kafka | `tool.executed`; calls Card API with JWT/tenant validated by the Core |
| conversation-memory-service | Redis; MongoDB | session with TTL, history, and long-term memory |
| knowledge-service | OpenSearch | vector index per tenant |
| conversation-audit-service | PostgreSQL | `ops.audit_events`, tenant/key deduplication |
| conversation-handoff-service | PostgreSQL | `conversation.handoffs`, tenant/key deduplication |
| renegotiation-service | PostgreSQL | idempotent simulation hash, status, and response |
| core-bancario-mock | Process memory | fixtures and process-local idempotency store for simulation/confirmation; lost on restart |

## Idempotency durability

| Layer | Durable after restart? | Role |
|---|---|---|
| Renegotiation Service/PostgreSQL | Yes | primary guarantee for the simulation journey |
| Core mock/memory | No | defense in depth and homologation determinism |
| BFF/Redis | depends on local persistence/TTL | outbound response deduplication |
| Audit/Handoff/PostgreSQL | Yes | side-effect deduplication |
| Memory/MongoDB | Yes | message deduplication by tenant/external ID |

The Core's in-memory state must not be interpreted as a banking database or as a replacement for durable domain-level idempotency.
