# Conversational AI Platform Architecture

[![Documentation](https://img.shields.io/badge/docs-MkDocs-526CFE?logo=materialformkdocs&logoColor=white)](https://leandrosflora.github.io/conversational-ai-platform-architecture/)
[![Publish MkDocs](https://github.com/leandrosflora/conversational-ai-platform-architecture/actions/workflows/docs.yml/badge.svg)](https://github.com/leandrosflora/conversational-ai-platform-architecture/actions/workflows/docs.yml)

Arquitetura de referência executável para plataformas de IA conversacional com agentes, MCP, RAG, WhatsApp, APIs corporativas, consistência transacional e observabilidade.

**Documentação:** https://leandrosflora.github.io/conversational-ai-platform-architecture/

## Documentação principal

- [Contexto de negócio](docs/context/business-context.md)
- [Arquitetura C4](docs/architecture/c4-context.md)
- [Jornadas e sequências](docs/architecture/sequence-diagrams.md)
- [Mapa de serviços](docs/contracts/services-map.md)
- [Contratos Kafka](docs/contracts/kafka-events.md)
- [Ownership de dados](docs/contracts/data-stores.md)
- [Arquitetura de segurança](docs/security/security-architecture.md)
- [Runbook](docs/runbook.md)
- [SLOs e alertas](docs/operations/slo-alerting.md)
- [Backup e recuperação](docs/operations/disaster-recovery.md)
- [Retenção e LGPD](docs/governance/data-retention-lgpd.md)
- [Carga e caos](docs/testing/load-and-chaos.md)
- [Roadmap de produção](docs/roadmap/production-readiness.md)

## Ambiente local

```bash
scripts/write-ci-env.sh
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

Parar:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml down
```

### Infraestrutura

| Serviço | Porta |
|---|---:|
| Redis | `6379` |
| MongoDB | `27018` |
| PostgreSQL | `5432` |
| Kafka | `29092` |
| Kafka UI | `8080` |
| OpenSearch | `9200` |
| Jaeger | `16686` |
| Loki | `3100` |
| Grafana Alloy | `12345` |
| Prometheus | `9090` |
| Alertmanager | `9093` |
| Grafana | `3001` |

Grafana é provisionado com Prometheus, Loki e Jaeger. Alloy coleta logs de containers. Prometheus carrega regras versionadas e envia alertas para o Alertmanager local.

## Repositórios de serviço

| Serviço | Repositório |
|---|---|
| Channel BFF | [whatsapp-bff](https://github.com/leandrosflora/whatsapp-bff) |
| Conversation Orchestrator | [conversation-orchestrator](https://github.com/leandrosflora/conversation-orchestrator) |
| Agent Runtime Renegociação | [agent-runtime-renegotiation](https://github.com/leandrosflora/agent-runtime-renegotiation) |
| Tool Service Renegociação | [tool-service-renegotiation](https://github.com/leandrosflora/tool-service-renegotiation) |
| Renegotiation Service | [renegotiation-service](https://github.com/leandrosflora/renegotiation-service) |
| Agent Runtime Cartão | [agent-runtime-fatura-cartao](https://github.com/leandrosflora/agent-runtime-fatura-cartao) |
| Tool Service Cartão | [tool-service-cartao-credito](https://github.com/leandrosflora/tool-service-cartao-credito) |
| Core Bancário Mock | [core-bancario-mock](https://github.com/leandrosflora/core-bancario-mock) |
| Knowledge Service | [knowledge-service](https://github.com/leandrosflora/knowledge-service) |
| Conversation Memory | [conversation-memory-service](https://github.com/leandrosflora/conversation-memory-service) |
| Conversation Audit | [conversation-audit-service](https://github.com/leandrosflora/conversation-audit-service) |
| Conversation Handoff | [conversation-handoff-service](https://github.com/leandrosflora/conversation-handoff-service) |

Os 12 repositórios possuem pipeline de build configurado. A cobertura de testes não é uniforme; o `core-bancario-mock` continua build-only até receber projeto de testes.

## CI e evidência

O CI deste repositório valida:

- Compose e contratos;
- Alloy, Prometheus e Alertmanager;
- scripts e documentação canônica;
- C4 e MkDocs;
- links;
- Trivy/SARIF;
- SBOM;
- smoke test real de infraestrutura.

O workflow `Multi-repository E2E` faz checkout dos 12 serviços, registra commits, executa builds/testes, sobe o stack, injeta um webhook assinado e publica evidências. Requer o secret `MULTIREPO_READ_TOKEN`.

## Kafka

Existem 9 tópicos. `channel.webhook.received` e `.retry` possuem consumers; `.dlq` é terminal. Os demais formam trilha de auditoria/observabilidade conforme a [matriz de eventos](docs/contracts/kafka-events.md).

## Segurança

Implementado:

- HMAC no webhook;
- JWT interno HS256 com segredo por par emissor/audiência;
- tenant assinado;
- policy determinística para tools de renegociação;
- Inbox/Outbox e idempotência;
- Trivy, SARIF e SBOM.

Bloqueadores de produção:

- autenticação/idempotência no Core mock;
- workload identity/JWKS ou mTLS;
- receivers reais e processo de incidentes;
- assinatura/atestado de imagens em todos os serviços;
- retenção/LGPD e DR corporativos.

Consulte o [roadmap de produção](docs/roadmap/production-readiness.md).
