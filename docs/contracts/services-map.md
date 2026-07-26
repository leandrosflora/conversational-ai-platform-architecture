# Mapa de serviços

**Fonte de verdade:** varredura do código-fonte de cada repositório, revisada contra execuções E2E e resincronizada em 2026-07-26. Este documento, junto com [`kafka-events.md`](kafka-events.md) e [`data-stores.md`](data-stores.md), é a referência canônica de portas, tópicos e serviços.

## Serviços implementados

| Serviço | Repo | Tipo | Entrada principal | Saída principal | Observação de implementação |
|---|---|---|---|---|---|
| whatsapp-bff | [leandrosflora/whatsapp-bff](https://github.com/leandrosflora/whatsapp-bff) | Channel BFF | Webhook WhatsApp (`POST /webhooks/whatsapp`) | `POST /messages` no Orchestrator; resposta via WhatsApp Cloud API | .NET 8; Kafka como fila durável de entrada, retry e DLQ; Redis para idempotência outbound |
| conversation-orchestrator | [leandrosflora/conversation-orchestrator](https://github.com/leandrosflora/conversation-orchestrator) | Orquestração/jornada | `POST /messages` | Outbox transacional: skill ativa, eventos, Audit, Handoff e resposta ao canal | .NET 8; Inbox+Outbox, lease por conversa, barreira de ordenação e roteamento das skills |
| agent-runtime-renegotiation | [leandrosflora/agent-runtime-renegotiation](https://github.com/leandrosflora/agent-runtime-renegotiation) | Agente de IA | `POST /process` | Tools MCP; Knowledge; `agent.events` | Python/FastAPI/Strands+OpenAI; snapshot configurável por `OPENAI_MODEL_ID` |
| tool-service-renegotiation | [leandrosflora/tool-service-renegotiation](https://github.com/leandrosflora/tool-service-renegotiation) | MCP tool server + REST mirror | MCP (`:8400`) ou REST (`:8401`) | Renegotiation Service; `tool.executed` | autorização determinística por estágio e identidade; não publica argumentos no Kafka |
| renegotiation-service | [leandrosflora/renegotiation-service](https://github.com/leandrosflora/renegotiation-service) | Gateway/BFF de domínio | 7 endpoints REST | APIs do Core Bancário mock | .NET 8; idempotência durável de simulação em PostgreSQL; assina JWT para o Core |
| agent-runtime-fatura-cartao | [leandrosflora/agent-runtime-fatura-cartao](https://github.com/leandrosflora/agent-runtime-fatura-cartao) | Agente de IA | `POST /process` | Tools MCP; `agent.events` | Python/FastAPI/Strands+OpenAI; guard determinístico de CPF |
| tool-service-cartao-credito | [leandrosflora/tool-service-cartao-credito](https://github.com/leandrosflora/tool-service-cartao-credito) | MCP tool server | MCP (2 tools) | Card API do Core; `tool.executed` | chamada somente leitura; envia JWT e tenant validados pelo Core; não envia `Idempotency-Key` nem policy proof |
| core-bancario-mock | [leandrosflora/core-bancario-mock](https://github.com/leandrosflora/core-bancario-mock) | Mock de sistema externo | 9 endpoints REST em `9401`–`9405` | — | .NET 8; CI com testes; health/métricas; autenticação por caller e tenant no Compose; idempotência process-local para simulação/confirmação |
| knowledge-service | [leandrosflora/knowledge-service](https://github.com/leandrosflora/knowledge-service) | RAG / busca | `GET /search`; `POST /admin/reindex` | OpenSearch e OpenAI Embeddings | PDFs por tenant e busca vetorial k-NN |
| conversation-memory-service | [leandrosflora/conversation-memory-service](https://github.com/leandrosflora/conversation-memory-service) | Memória conversacional | sessões, histórico e memória | Redis e MongoDB | escrito pelo Orchestrator via Outbox; chaves tenant-scoped |
| conversation-audit-service | [leandrosflora/conversation-audit-service](https://github.com/leandrosflora/conversation-audit-service) | Audit Service | `POST /journey-events` | PostgreSQL | dedup por tenant e chave de idempotência |
| conversation-handoff-service | [leandrosflora/conversation-handoff-service](https://github.com/leandrosflora/conversation-handoff-service) | Handoff Service | `POST /handoffs` | PostgreSQL | dedup por tenant e chave de idempotência |
| alertmanager | Neste repositório | Infraestrutura de alertas | API/UI (`:9093`) | receiver local nulo | agrupa, inibe e roteia alertas; receiver externo permanece pendente |

## Sistemas somente da arquitetura-alvo

| Sistema | Integração atual | Situação alvo |
|---|---|---|
| Salesforce CRM | Nenhuma | origem de segmentação/campanhas |
| Data Lake Corporativo | Nenhuma | analytics e retenção regulatória |
| Produto de Dados / Automação | Nenhuma | ativação de clientes |
| Base de Conhecimento Corporativa | PDFs locais | conector governado e ACL por documento |
| Plataforma de Atendimento | Handoff persiste solicitação | fila humana e integração bidirecional |

## Regra de leitura

- **Implementado:** confirmado em código, Compose e/ou evidência E2E.
- **Provisionado:** container ou infraestrutura disponível.
- **Alvo:** capacidade planejada sem integração executável.
