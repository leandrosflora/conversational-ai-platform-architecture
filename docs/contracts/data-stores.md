# Datastores

**Fonte de verdade:** varredura do código-fonte em 2026-07-17, atualizada em 2026-07-26 com os dois serviços da skill de fatura/limite de cartão de crédito e, na mesma data, revarrida por completo — o Orchestrator ganhou um Inbox/Outbox transacional em PostgreSQL desde a última varredura, e o `renegotiation-service`/`whatsapp-bff` já não são totalmente stateless (ver [`services-map.md`](services-map.md)).

## O que está provisionado vs. o que é realmente usado

`docker-compose.yml` (neste repositório) sobe PostgreSQL, MongoDB, Redis, Kafka e OpenSearch como infraestrutura local. **Todos os cinco são efetivamente lidos/escritos por serviços implementados hoje.**

| Datastore | Provisionado em `docker-compose.yml`? | Usado por algum serviço hoje? |
|---|---|---|
| Kafka | Sim | **Sim** — whatsapp-bff, conversation-orchestrator, agent-runtime-renegotiation, tool-service-renegotiation, agent-runtime-fatura-cartao, tool-service-cartao-credito |
| PostgreSQL | Sim | **Sim** — conversation-orchestrator (`ops.message_inbox`, `ops.conversation_state`, `ops.orchestrator_outbox`), conversation-audit-service (`ops.audit_events`), conversation-handoff-service (`conversation.handoffs`), renegotiation-service (idempotência de simulação) |
| MongoDB | Sim | **Sim** — conversation-memory-service (`conversation_messages`, `agent_memory`) |
| Redis | Sim | **Sim** — conversation-memory-service (sessão ativa), whatsapp-bff (idempotência de `POST /internal/messages`) |
| OpenSearch | Sim | **Sim** — knowledge-service (índice por tenant, busca vetorial k-NN) |

## Por serviço

| Serviço | Datastore usado | Detalhe |
|---|---|---|
| whatsapp-bff | Kafka; Redis | Kafka: produtor/consumidor de `channel.webhook.received` + `.retry`, produtor de `.dlq`, `channel.message.received`/`channel.message.status`. Redis: reserva de idempotência de `POST /internal/messages` por tenant + `Idempotency-Key` |
| conversation-orchestrator | PostgreSQL; Kafka (produtor, via Outbox) | PostgreSQL: `ops.message_inbox` (dedup/lease por mensagem), `ops.conversation_state` (estágio/versão/skill por conversa), `ops.orchestrator_outbox` (efeitos pendentes: memória, auditoria, handoff, resposta ao canal, eventos Kafka). `intent.detected`/`conversation.state_changed` são dois desses efeitos, despachados em background, não publicados de forma síncrona no request |
| agent-runtime-renegotiation | Kafka (produtor) | `agent.events` — já chama `knowledge-service` via `GET /search` (`app/tools/knowledge.py`) |
| tool-service-renegotiation | Kafka (produtor) | `tool.executed` |
| agent-runtime-fatura-cartao | Kafka (produtor) | `agent.events` — sem chamada a `knowledge-service` nem `conversation-memory-service` |
| tool-service-cartao-credito | Kafka (produtor) | `tool.executed` — chama `core-bancario-mock` (Card API) diretamente, com JWT assinado (não validado pelo mock) |
| conversation-memory-service | Redis; MongoDB | Redis: sessão ativa por conversa, com TTL, chave `tenant:{tenantId}:session:{conversationId}` (`GET`/`PUT`/`DELETE /sessions/{conversation_id}`). MongoDB: histórico de mensagens em `conversation_messages` (`/conversations/{id}/messages`) e fatos de memória de longo prazo em `agent_memory` (`/users/{id}/memory`) |
| knowledge-service | OpenSearch | Índice por tenant `faq_chunks-{tenantId}` (k-NN vector search sobre embeddings OpenAI). Ingestão de PDFs de FAQ em `data/faq_pdfs/{tenantId}/`, no startup e via `POST /admin/reindex` |
| conversation-audit-service | PostgreSQL | `POST /journey-events` grava uma linha em `ops.audit_events` por evento (`tenant_id` resolvido do request, `idempotency_key` do header, `actor_type='system'`, `action='conversation.journey_processed'`); deduplicado por `(tenant_id, idempotency_key)` |
| conversation-handoff-service | PostgreSQL | `POST /handoffs` grava uma linha em `conversation.handoffs` por pedido (`tenant_id` do request, `conversation_id` ainda aponta para uma conversa seed fixa via FK, `target_queue='human-support'`, `reason` repassado, `metadata.externalConversationId` com o ID real da conversa); deduplicado por `(tenant_id, idempotency_key)` |
| renegotiation-service | PostgreSQL | Idempotência de simulação: uma linha por `Idempotency-Key`, com o hash da requisição e a resposta obtida do Core Bancário — chave repetida com o mesmo request não chama o Core Bancário de novo |
| core-bancario-mock | Nenhum | Dados fake gerados inline a cada chamada |

## Por que isso importa

Nenhum datastore provisionado neste workspace está mais na categoria "só provisionado, sem consumidor real". Além dos consumidores já estabelecidos (`conversation-memory-service` → Redis/MongoDB, `knowledge-service` → OpenSearch, `conversation-audit-service`/`conversation-handoff-service` → PostgreSQL), o próprio `conversation-orchestrator` passou a persistir diretamente em PostgreSQL (Inbox/Outbox transacional — antes não tinha banco próprio), `renegotiation-service` passou a usar PostgreSQL para idempotência de simulação (antes era totalmente stateless), e `whatsapp-bff` passou a usar Redis para idempotência de resposta outbound. Uma leitura deste documento que assuma "o Orchestrator não tem banco direto" ou "o `renegotiation-service` é totalmente stateless" está desatualizada.
