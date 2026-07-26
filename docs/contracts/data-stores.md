# Datastores

**Fonte de verdade:** varredura dos repositórios e Compose, resincronizada em 2026-07-26.

## Infraestrutura provisionada e uso real

| Datastore | Provisionado? | Consumidores implementados |
|---|---|---|
| Kafka | Sim | whatsapp-bff, conversation-orchestrator, agent runtimes e tool services |
| PostgreSQL | Sim | Orchestrator, Audit, Handoff e Renegotiation Service |
| MongoDB | Sim | Conversation Memory |
| Redis | Sim | Conversation Memory e whatsapp-bff |
| OpenSearch | Sim | Knowledge Service |

Todos os datastores provisionados possuem consumidor real.

## Por serviço

| Serviço | Datastore/estado | Detalhe |
|---|---|---|
| whatsapp-bff | Kafka; Redis | entrada/retry/DLQ e dedupe outbound por tenant/chave |
| conversation-orchestrator | PostgreSQL; Kafka | Inbox, estado versionado, Outbox e eventos assíncronos |
| agent-runtime-renegotiation | Kafka | `agent.events`; consulta Knowledge |
| tool-service-renegotiation | Kafka | `tool.executed` |
| agent-runtime-fatura-cartao | Kafka | `agent.events` |
| tool-service-cartao-credito | Kafka | `tool.executed`; chama Card API com JWT/tenant validados pelo Core |
| conversation-memory-service | Redis; MongoDB | sessão com TTL, histórico e memória de longo prazo |
| knowledge-service | OpenSearch | índice vetorial por tenant |
| conversation-audit-service | PostgreSQL | `ops.audit_events`, dedupe tenant/chave |
| conversation-handoff-service | PostgreSQL | `conversation.handoffs`, dedupe tenant/chave |
| renegotiation-service | PostgreSQL | hash, status e resposta idempotentes da simulação |
| core-bancario-mock | Memória do processo | fixtures e store idempotente process-local de simulação/confirmação; perdido no restart |

## Durabilidade da idempotência

| Camada | Durável após restart? | Papel |
|---|---|---|
| Renegotiation Service/PostgreSQL | Sim | garantia principal da jornada de simulação |
| Core mock/memória | Não | defesa em profundidade e determinismo de homologação |
| BFF/Redis | conforme persistência/TTL local | dedupe de resposta outbound |
| Audit/Handoff/PostgreSQL | Sim | dedupe de side effects |
| Memory/MongoDB | Sim | dedupe de mensagens por tenant/external ID |

O estado em memória do Core não deve ser interpretado como banco de dados bancário nem como substituto da idempotência durável no domínio.
