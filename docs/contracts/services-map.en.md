# Services Map

**Source of truth:** source-code scan of each repository, reviewed against E2E executions and resynchronized on 2026-07-26. This document, together with [`kafka-events.md`](kafka-events.md) and [`data-stores.md`](data-stores.md), is the canonical reference for ports, topics, and services.

## Implemented services

| Service | Repo | Type | Main input | Main output | Implementation note |
|---|---|---|---|---|---|
| whatsapp-bff | [leandrosflora/whatsapp-bff](https://github.com/leandrosflora/whatsapp-bff) | Channel BFF | WhatsApp webhook (`POST /webhooks/whatsapp`) | `POST /messages` to Orchestrator; response through WhatsApp Cloud API | .NET 8; Kafka as durable ingress queue, retry, and DLQ; Redis for outbound idempotency |
| conversation-orchestrator | [leandrosflora/conversation-orchestrator](https://github.com/leandrosflora/conversation-orchestrator) | Orchestration/journey | `POST /messages` | Transactional Outbox: active skill, events, Audit, Handoff, and channel response | .NET 8; Inbox+Outbox, conversation lease, ordering barrier, and skill routing |
| agent-runtime-renegotiation | [leandrosflora/agent-runtime-renegotiation](https://github.com/leandrosflora/agent-runtime-renegotiation) | AI agent | `POST /process` | MCP tools; Knowledge; `agent.events` | Python/FastAPI/Strands+OpenAI; model snapshot configurable through `OPENAI_MODEL_ID` |
| tool-service-renegotiation | [leandrosflora/tool-service-renegotiation](https://github.com/leandrosflora/tool-service-renegotiation) | MCP tool server + REST mirror | MCP (`:8400`) or REST (`:8401`) | Renegotiation Service; `tool.executed` | deterministic authorization by stage and identity; tool arguments are not published to Kafka |
| renegotiation-service | [leandrosflora/renegotiation-service](https://github.com/leandrosflora/renegotiation-service) | Domain Gateway/BFF | 7 REST endpoints | Banking Core mock APIs | .NET 8; durable simulation idempotency in PostgreSQL; signs JWT for the Core |
| agent-runtime-fatura-cartao | [leandrosflora/agent-runtime-fatura-cartao](https://github.com/leandrosflora/agent-runtime-fatura-cartao) | AI agent | `POST /process` | MCP tools; `agent.events` | Python/FastAPI/Strands+OpenAI; deterministic tax-ID guard |
| tool-service-cartao-credito | [leandrosflora/tool-service-cartao-credito](https://github.com/leandrosflora/tool-service-cartao-credito) | MCP tool server | MCP (2 tools) | Core Card API; `tool.executed` | read-only calls; sends JWT and tenant validated by the Core; does not send `Idempotency-Key` or policy proof |
| core-bancario-mock | [leandrosflora/core-bancario-mock](https://github.com/leandrosflora/core-bancario-mock) | External-system mock | 9 REST endpoints on `9401`–`9405` | — | .NET 8; CI with tests; health/metrics; caller and tenant authentication in Compose; process-local idempotency for simulation/confirmation |
| knowledge-service | [leandrosflora/knowledge-service](https://github.com/leandrosflora/knowledge-service) | RAG / search | `GET /search`; `POST /admin/reindex` | OpenSearch and OpenAI Embeddings | PDFs per tenant and vector k-NN search |
| conversation-memory-service | [leandrosflora/conversation-memory-service](https://github.com/leandrosflora/conversation-memory-service) | Conversational memory | sessions, history, and memory | Redis and MongoDB | written by the Orchestrator through Outbox; tenant-scoped keys |
| conversation-audit-service | [leandrosflora/conversation-audit-service](https://github.com/leandrosflora/conversation-audit-service) | Audit Service | `POST /journey-events` | PostgreSQL | deduplication by tenant and idempotency key |
| conversation-handoff-service | [leandrosflora/conversation-handoff-service](https://github.com/leandrosflora/conversation-handoff-service) | Handoff Service | `POST /handoffs` | PostgreSQL | deduplication by tenant and idempotency key |
| alertmanager | This repository | Alerting infrastructure | API/UI (`:9093`) | local null receiver | groups, inhibits, and routes alerts; external receiver remains pending |

## Systems that exist only in the target architecture

| System | Current integration | Target state |
|---|---|---|
| Salesforce CRM | None | source of segmentation/campaigns |
| Enterprise Data Lake | None | analytics and regulatory retention |
| Data Product / Automation | None | customer activation |
| Enterprise Knowledge Base | Local PDFs | governed connector and document-level ACL |
| Customer Service Platform | Handoff persists request | human queue and bidirectional integration |

## Reading rule

- **Implemented:** confirmed in code, Compose, and/or E2E evidence.
- **Provisioned:** container or infrastructure is available.
- **Target:** planned capability without executable integration.
