# Mapa de serviços

**Fonte de verdade:** varredura do código-fonte de cada repositório, feita em 2026-07-06, revisada contra uma execução real da jornada E2E em 2026-07-13, complementada em 2026-07-17 com conhecimento e memória, em 2026-07-18 com auditoria e handoff e em 2026-07-26 com a skill de fatura/limite de cartão. A última resincronização completa ocorreu em 2026-07-26. Este documento, junto com [`kafka-events.md`](kafka-events.md) e [`data-stores.md`](data-stores.md), é a referência canônica de portas, tópicos e serviços.

## Serviços implementados

| Serviço | Repo | Tipo | Entrada principal | Saída principal | Observação de implementação |
|---|---|---|---|---|---|
| whatsapp-bff | [leandrosflora/whatsapp-bff](https://github.com/leandrosflora/whatsapp-bff) | Channel BFF | Webhook WhatsApp (`POST /webhooks/whatsapp`) | `POST /messages` no Orchestrator; resposta via WhatsApp Cloud API | .NET 8; Kafka como fila durável de entrada, com retry (`channel.webhook.received.retry`) e DLQ (`.dlq`) próprios; Redis para idempotência de `POST /internal/messages` |
| conversation-orchestrator | [leandrosflora/conversation-orchestrator](https://github.com/leandrosflora/conversation-orchestrator) | Orquestração/jornada | `POST /messages` | Outbox transacional: skill ativa, eventos Kafka, Audit Service, Handoff Service e resposta ao canal | .NET 8; Inbox+Outbox transacional, lease por conversa, barreira de ordenação e roteamento das skills `renegotiation` e `cartao-credito` |
| agent-runtime-renegotiation | [leandrosflora/agent-runtime-renegotiation](https://github.com/leandrosflora/agent-runtime-renegotiation) | Agente de IA | `POST /process` | Tools MCP; Knowledge Service; `agent.events` | Python/FastAPI/Strands+OpenAI; threshold 0.6; snapshot de homologação configurável por `OPENAI_MODEL_ID` |
| tool-service-renegotiation | [leandrosflora/tool-service-renegotiation](https://github.com/leandrosflora/tool-service-renegotiation) | MCP tool server + REST mirror | MCP (7 tools, `:8400`) ou REST (`:8401`) | Renegotiation Service; `tool.executed` | Python/FastMCP; autorização por estágio e identidade do chamador; não publica argumentos no Kafka |
| renegotiation-service | [leandrosflora/renegotiation-service](https://github.com/leandrosflora/renegotiation-service) | Gateway/BFF de domínio | 7 endpoints REST | 4 APIs do Core Bancário mock | .NET 8; sem Kafka; pass-through; idempotência de simulação em PostgreSQL |
| agent-runtime-fatura-cartao | [leandrosflora/agent-runtime-fatura-cartao](https://github.com/leandrosflora/agent-runtime-fatura-cartao) | Agente de IA | `POST /process` | Tools MCP; `agent.events` | Python/FastAPI/Strands+OpenAI; porta `8110`; guard determinístico de CPF; sem Knowledge Service ou Conversation Memory |
| tool-service-cartao-credito | [leandrosflora/tool-service-cartao-credito](https://github.com/leandrosflora/tool-service-cartao-credito) | MCP tool server | MCP (2 tools) | Card API do Core Bancário mock; `tool.executed` | Python/FastMCP; portas `8410`/`8411`; chamada direta sem serviço de domínio intermediário; envia JWT de serviço ao mock, que ainda não o valida; não envia `Idempotency-Key` e não publica CPF no Kafka |
| core-bancario-mock | [leandrosflora/core-bancario-mock](https://github.com/leandrosflora/core-bancario-mock) | Mock de sistema externo | 9 endpoints REST em `9401`-`9405` | — | .NET 8, processo único, sem persistência; repositório próprio privado; ainda sem workflow de CI; não valida JWT em nenhuma das cinco APIs |
| knowledge-service | [leandrosflora/knowledge-service](https://github.com/leandrosflora/knowledge-service) | RAG / busca | `GET /search`; `POST /admin/reindex` | OpenSearch e OpenAI Embeddings | Python/FastAPI; porta `8500`; PDFs por tenant e busca vetorial k-NN |
| conversation-memory-service | [leandrosflora/conversation-memory-service](https://github.com/leandrosflora/conversation-memory-service) | Memória conversacional | Sessões, histórico e memória de usuário | Redis e MongoDB | Python/FastAPI; porta `8600`; escrito pelo Orchestrator via Outbox |
| conversation-audit-service | [leandrosflora/conversation-audit-service](https://github.com/leandrosflora/conversation-audit-service) | Audit Service | `POST /journey-events` | PostgreSQL (`ops.audit_events`) | .NET 8; porta `8300`; dedup por tenant e chave de idempotência |
| conversation-handoff-service | [leandrosflora/conversation-handoff-service](https://github.com/leandrosflora/conversation-handoff-service) | Handoff Service | `POST /handoffs` | PostgreSQL (`conversation.handoffs`) | .NET 8; porta `8200`; dedup por tenant e chave de idempotência |

## Sistemas somente da arquitetura-alvo

Os elementos abaixo aparecem no **C4 de contexto alvo**, mas não possuem integração executável neste workspace.

| Sistema | Integração atual | Situação alvo |
|---|---|---|
| Salesforce CRM | Nenhuma | Origem da segmentação de campanhas via Data Lake |
| Data Lake Corporativo | Nenhuma | Analytics, retenção regulatória e exportação de auditoria |
| Produto de Dados / Automação de Campanha | Nenhuma | Ativação de clientes em canais externos |
| Base de Conhecimento Corporativa | PDFs locais montados no `knowledge-service` | Conector governado, classificação e ACL por documento |
| Plataforma de Atendimento | O Handoff Service apenas persiste solicitações | Fila humana e integração bidirecional com desktop do atendente |

## Regra de leitura

- **Implementado:** confirmado em código, Compose e/ou evidência E2E.
- **Provisionado:** container ou infraestrutura disponível, ainda que alguma aplicação não publique dados completos.
- **Alvo:** capacidade corporativa planejada, sem integração executável neste workspace.
