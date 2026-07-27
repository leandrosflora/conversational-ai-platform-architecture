# Conversational AI Platform Architecture

[![Documentation](https://img.shields.io/badge/docs-MkDocs-526CFE?logo=materialformkdocs&logoColor=white)](https://leandrosflora.github.io/conversational-ai-platform-architecture/)
[![Publish MkDocs](https://github.com/leandrosflora/conversational-ai-platform-architecture/actions/workflows/docs.yml/badge.svg)](https://github.com/leandrosflora/conversational-ai-platform-architecture/actions/workflows/docs.yml)

Arquitetura de referência executável para IA conversacional com agentes, MCP, RAG, WhatsApp, APIs corporativas, consistência transacional, segurança interna, contratos executáveis e observabilidade.

**Documentação:** https://leandrosflora.github.io/conversational-ai-platform-architecture/

## Documentação

- [Contexto de negócio](docs/context/business-context.md)
- [Arquitetura C4](docs/architecture/c4-context.md)
- [Jornadas e sequências](docs/architecture/sequence-diagrams.md)
- [Mapa de serviços](docs/contracts/services-map.md)
- [Contratos Kafka](docs/contracts/kafka-events.md)
- [Ownership de dados](docs/contracts/data-stores.md)
- [Arquitetura de segurança](docs/security/security-architecture.md)
- [Release e contratos executáveis](docs/governance/release-contract-governance.md)
- [Workload Identity e PDP](docs/security/workload-identity-pdp.md)
- [Evals de IA](docs/testing/evals.md)
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

Grafana é provisionado com Prometheus, Loki e Jaeger. Alloy coleta logs. Prometheus carrega regras versionadas e envia alertas para o Alertmanager local.

## Validações P8

```bash
python -m pip install pyyaml
python scripts/validate-executable-contracts.py
python scripts/run-evals.py --mode offline --output artifacts/evals-offline.json
```

Profile local de identidade assimétrica e policy centralizada:

```bash
docker compose -f docker-compose.security.yml up -d --build --wait
python scripts/validate-security-control-plane.py
docker compose -f docker-compose.security.yml down -v
```

O `release/release-manifest.yaml` é resolvido para um lock com SHAs exatos antes do E2E multi-repositório. O lock, e não as branches móveis, é a unidade de promoção e rollback.

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

Os 12 repositórios possuem pipeline de build. O Core executa testes de integração de health, autenticação e idempotência. O change set P8 adiciona CodeQL, dependency review, Trivy, SBOM e atestações de release de forma uniforme nos serviços.

## CI e evidência

O CI deste repositório valida:

- Compose e contratos canônicos;
- contratos OpenAPI, AsyncAPI e autorização;
- manifesto de release e inventário de repositórios;
- evals determinísticos;
- OPA e profile JWKS/RS256;
- Alloy, Prometheus e Alertmanager;
- scripts, C4, MkDocs e links;
- Trivy/SARIF e SBOM;
- smoke test real da infraestrutura.

O workflow `Multi-repository E2E` resolve os 13 repositórios para SHAs, registra um release lock, executa builds/testes, sobe o stack, injeta webhook assinado, valida o Core autenticado, executa evals online e carga k6, e publica evidências. Requer `MULTIREPO_READ_TOKEN`.

## Kafka

Existem 9 tópicos. `channel.webhook.received` e `.retry` possuem consumers; `.dlq` é terminal. Os demais formam trilha de auditoria/observabilidade conforme a [matriz de eventos](docs/contracts/kafka-events.md).

## Segurança

Implementado no profile padrão:

- HMAC no webhook;
- JWT interno HS256 com segredo por par;
- tenant assinado;
- policy determinística de tools;
- Core com caller, tenant e idempotência validados;
- Inbox/Outbox;
- Trivy, SARIF e SBOM.

Implementado como profile de migração executável:

- tokens RS256;
- descoberta OIDC e JWKS;
- allowlist por workload/audience;
- OPA como PDP centralizado;
- testes de evidência financeira e tenant.

Bloqueadores corporativos restantes:

- integrar os serviços ao emissor corporativo/SPIFFE em modo dual e depois remover HS256;
- HSM/KMS, rotação, revogação e mTLS;
- persistência real/idempotente no sistema bancário final;
- receivers reais e processo de incidentes;
- retenção/LGPD e DR regional.

Consulte o [roadmap de produção](docs/roadmap/production-readiness.md).
