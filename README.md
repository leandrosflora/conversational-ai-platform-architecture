# Conversational AI Platform Architecture

[![Documentation](https://img.shields.io/badge/docs-MkDocs-526CFE?logo=materialformkdocs&logoColor=white)](https://leandrosflora.github.io/conversational-ai-platform-architecture/)
[![Publish MkDocs](https://github.com/leandrosflora/conversational-ai-platform-architecture/actions/workflows/docs.yml/badge.svg)](https://github.com/leandrosflora/conversational-ai-platform-architecture/actions/workflows/docs.yml)

**Documentação publicada:** https://leandrosflora.github.io/conversational-ai-platform-architecture/

Arquitetura de referência para plataformas de IA conversacional utilizando agentes, MCP, RAG, WhatsApp, APIs corporativas e observabilidade ponta a ponta.

## Documentação

- [Contexto de negócio](docs/context/business-context.md) — jornadas, personas e escopo.
- [C4 nível 1](docs/architecture/c4-context.md) — separação explícita entre estado implementado e arquitetura-alvo corporativa.
- [Diagramas de sequência da jornada](docs/architecture/sequence-diagrams.md) — passo a passo técnico, do webhook do WhatsApp até a consulta de débitos/elegibilidade.
- [Páginas de referência por serviço](docs/services/) — responsabilidade, APIs, eventos e regras de negócio de cada um dos 12 serviços implementados.
- [Contratos](docs/contracts/) — mapa de serviços, matriz de eventos Kafka, datastores.
- [ADRs](docs/adr/) — decisões de arquitetura já implementadas no código.
- [Arquitetura de segurança](docs/security/security-architecture.md).
- [Runbook do ambiente local](docs/runbook.md) — como subir a infraestrutura e os serviços de aplicação.
- [Plano de atualização de dependências](docs/roadmap/platform-dependency-upgrades.md) — Kafka, Jaeger e Loki.
- [Validações E2E](docs/validation/) — execuções reais da jornada completa contra os serviços rodando, comparando comportamento observado com o que os docs afirmam.

## Ambiente local

Subir infraestrutura local:

```bash
docker compose up -d
```

Parar e remover containers:

```bash
docker compose down
```

Remover containers e volumes:

```bash
docker compose down -v
```

### Serviços

| Serviço | URL/porta local | Credenciais |
| --- | --- | --- |
| Redis | `localhost:6379` | - |
| MongoDB | `localhost:27018` | `admin/admin` |
| PostgreSQL | `localhost:5432` | `postgres/postgres` |
| Kafka | `localhost:29092` | - |
| OpenSearch | `localhost:9200` | - |
| Jaeger UI | `localhost:16686` | - |
| Loki | `localhost:3100` | - |
| Grafana Alloy | `localhost:12345` | - |
| Prometheus | `localhost:9090` | - |
| Grafana | `localhost:3001` | `admin/admin` |

### Observabilidade

O Grafana sobe provisionado com datasources para Prometheus, Loki e Jaeger. O Grafana Alloy descobre os containers pelo Docker socket, preserva os labels `container`, `service` e `stream` e envia os logs ao Loki. O Prometheus coleta métricas dele mesmo, do Jaeger, do Alloy e dos endpoints `/metrics` declarados para os serviços de aplicação.

Os serviços já propagam `TraceId`/`SpanId`/`CorrelationId` e exportam traces por OTLP quando instrumentados. Nem todos os endpoints de métricas de aplicação estão implementados; portanto, alguns targets podem aparecer como `DOWN` sem comprometer a saúde da infraestrutura local.

Promtail não é mais iniciado no stack padrão. Ele permanece apenas no perfil de rollback explícito:

```bash
docker compose --profile legacy-promtail up -d promtail
```

## Repositórios envolvidos

| Serviço | Repositório |
|---|---|
| Channel BFF | [whatsapp-bff](https://github.com/leandrosflora/whatsapp-bff) |
| Conversation Orchestrator | [conversation-orchestrator](https://github.com/leandrosflora/conversation-orchestrator) |
| Agent Runtime | [agent-runtime-renegotiation](https://github.com/leandrosflora/agent-runtime-renegotiation) |
| Tool Service (MCP) | [tool-service-renegotiation](https://github.com/leandrosflora/tool-service-renegotiation) |
| Renegotiation Service | [renegotiation-service](https://github.com/leandrosflora/renegotiation-service) |
| Agent Runtime (fatura de cartão) | [agent-runtime-fatura-cartao](https://github.com/leandrosflora/agent-runtime-fatura-cartao) |
| Tool Service (fatura de cartão, MCP) | [tool-service-cartao-credito](https://github.com/leandrosflora/tool-service-cartao-credito) |
| Core Bancário (mock) | [core-bancario-mock](https://github.com/leandrosflora/core-bancario-mock) |
| Knowledge Service | [knowledge-service](https://github.com/leandrosflora/knowledge-service) |
| Conversation Memory Service | [conversation-memory-service](https://github.com/leandrosflora/conversation-memory-service) |
| Conversation Audit Service | [conversation-audit-service](https://github.com/leandrosflora/conversation-audit-service) |
| Conversation Handoff Service | [conversation-handoff-service](https://github.com/leandrosflora/conversation-handoff-service) |

Detalhe de responsabilidades, APIs e regras de negócio de cada um em [`docs/services/`](docs/services/).

Os 11 repositórios de serviço públicos/privados com pipeline configurado executam build e testes a cada push/PR. O `core-bancario-mock` possui repositório próprio, mas ainda precisa receber um workflow de CI. Este repositório valida MkDocs, configuração do Compose e executa smoke test real da infraestrutura.

## Kafka em prática

**9 tópicos** existem hoje no código. `channel.webhook.received` e `channel.webhook.received.retry` possuem produtor e consumidor implementados no `whatsapp-bff`; `channel.webhook.received.dlq` é o fim de linha intencional. Os seis tópicos restantes são publicados como trilha de auditoria/observabilidade e ainda não têm consumidores de aplicação. Matriz completa em [`docs/contracts/kafka-events.md`](docs/contracts/kafka-events.md).

## Dados e bancos

Kafka, PostgreSQL, MongoDB, Redis e OpenSearch são efetivamente usados por código de aplicação hoje: PostgreSQL pelo `conversation-audit-service`, `conversation-handoff-service`, `conversation-orchestrator` e `renegotiation-service`; MongoDB pelo `conversation-memory-service`; Redis pelo `conversation-memory-service` e `whatsapp-bff`; OpenSearch pelo `knowledge-service`. Detalhe em [`docs/contracts/data-stores.md`](docs/contracts/data-stores.md).

## Contratos

- [Mapa de serviços](docs/contracts/services-map.md) — todos os serviços implementados e as dependências assumidas.
- [Eventos Kafka](docs/contracts/kafka-events.md) — matriz produtor/consumidor/status.
- [Datastores](docs/contracts/data-stores.md) — o que é provisionado e o que é usado.

## Segurança

Validação HMAC do webhook, exclusão de dados sensíveis dos eventos de auditoria, JWT interno HS256 com segredo distinto por par emissor/audiência e tokens `governed_tool` com autorização por estágio de jornada entre `agent-runtime-renegotiation` → `tool-service-renegotiation` → `renegotiation-service`. Lacunas conhecidas: sem criptografia em repouso, e o HS256 por par ainda é simétrico sem rotação automatizada. Consulte [`docs/security/security-architecture.md`](docs/security/security-architecture.md) e as evidências em `docs/validation/`.

## ADRs

Decisões já implementadas, registradas em [`docs/adr/`](docs/adr/): Kafka como fila durável de webhook, arquitetura hexagonal nos serviços .NET, MCP para tool-calling governado, resiliência `catch-log-continue` e Inbox/Outbox transacional.
