# Runbook — Plataforma de IA Conversacional

## 1. Escopo e classificação

Este runbook descreve o estado do branch `main` do repositório `conversational-ai-platform-architecture`. A solução é uma referência executável/POC endurecida; não é classificada como production-ready bancário.

A arquitetura-alvo permanece em `docs/architecture/C4/c4-container-target.puml`.

## 2. Layout do workspace

Os repositórios devem ficar como pastas irmãs:

```text
workspace/
├── conversational-ai-platform-architecture/
├── whatsapp-bff/
├── conversation-orchestrator/
├── agent-runtime-renegotiation/
├── tool-service-renegotiation/
├── renegotiation-service/
├── agent-runtime-fatura-cartao/
├── tool-service-cartao-credito/
├── knowledge-service/
├── conversation-memory-service/
├── conversation-audit-service/
├── conversation-handoff-service/
└── core-bancario-mock/
```

Mudanças de tenant, autenticação, contratos ou journey state exigem implantação e validação coordenadas.

## 3. Configuração

Crie `.env` na raiz do repositório de arquitetura. Use `.env.example` como fonte canônica. Cada par emissor/audiência possui segredo independente no ambiente local.

```bash
cp .env.example .env
```

Gere segredos locais com pelo menos 32 bytes:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Nunca versione valores reais.

## 4. Validações antes do merge

O CI executa:

- validação do Docker Compose;
- deriva Compose × contratos;
- configuração Alloy, Prometheus e Alertmanager;
- sintaxe de scripts;
- frescor da documentação canônica;
- geração/verificação dos diagramas C4;
- MkDocs strict;
- links;
- Trivy, SARIF e SBOM;
- smoke test real da infraestrutura.

Cada repositório de serviço também precisa executar build/testes próprios. O `core-bancario-mock` já possui CI de restore/build, mas ainda não possui projeto de testes.

## 5. Subida local

```bash
scripts/write-ci-env.sh
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.override.yml ps
```

## 6. Portas

| Serviço | Porta host | Sinal |
|---|---:|---|
| whatsapp-bff | `5153` | `/health/ready` |
| conversation-orchestrator | `5268` | `/health/ready` |
| agent-runtime-renegotiation | `8100` | `/health/ready` |
| agent-runtime-fatura-cartao | `8110` | `/health/ready` |
| conversation-handoff-service | `8200` | `/health/ready` |
| conversation-audit-service | `8300` | `/health/ready` |
| tool-service-renegotiation REST | `8401` | `/health/ready` |
| tool-service-cartao-credito REST | `8411` | `/health/ready` |
| knowledge-service | `8500` | `/health/ready` |
| conversation-memory-service | `8600` | `/health/ready` |
| renegotiation-service | `5266` | `/health/ready` |
| core-bancario-mock | `9401`–`9405` | health dedicado pendente |
| Kafka UI | `8080` | UI |
| Jaeger | `16686` | UI |
| Prometheus | `9090` | UI/API |
| Alertmanager | `9093` | UI/API |
| Grafana | `3001` | UI |
| Alloy | `12345` | UI/ready |

## 7. Autenticação interna

Chamadas internas usam:

```text
Authorization: Bearer <JWT>
X-Tenant-Id: <UUID>
```

Claims comuns:

```text
iss, sub, aud, iat, exp, jti, tenant_id, kid
```

Resultados esperados:

- sem token: `401`;
- tenant ausente ou inválido: `400`;
- header diferente da claim: `403`;
- caller/audiência não permitidos: `403`.

A exceção atual é o `core-bancario-mock`, que recebe headers em alguns hops mas ainda não os valida.

## 8. Persistência e consistência

PostgreSQL:

```text
ops.message_inbox
ops.conversation_state
ops.orchestrator_outbox
ops.renegotiation_idempotency
ops.audit_events
conversation.handoffs
```

MongoDB:

```text
conversation_messages
unique partial index: (tenantId, externalMessageId)
```

OpenSearch:

```text
faq_chunks-<tenant-uuid>
```

O `202` do Orchestrator significa que estado e efeitos obrigatórios foram registrados; não significa que todos os downstreams já concluíram.

## 9. Kafka

Tópicos críticos:

```text
channel.webhook.received
channel.webhook.received.retry
channel.webhook.received.dlq
```

O offset original só é commitado após processamento ou publicação confirmada em retry/DLQ.

## 10. Observabilidade e alertas

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d \
  jaeger loki alloy alertmanager prometheus grafana
```

Prometheus carrega regras de `config/prometheus/rules/`. Alertmanager local usa receiver nulo para não enviar notificações acidentalmente.

Consulte:

- `docs/operations/slo-alerting.md`;
- `http://localhost:9090/alerts`;
- `http://localhost:9093`;
- `http://localhost:3001`.

## 11. E2E multi-repositório

Execução local:

```bash
scripts/e2e-multirepo.sh
```

O script:

1. registra o commit de cada repositório;
2. executa build/testes .NET e Python;
3. sobe o Compose completo;
4. espera readiness;
5. envia webhook Meta assinado;
6. verifica o Inbox do Orchestrator;
7. valida Core/Card, Kafka, Prometheus e evidências;
8. executa um baseline k6.

No GitHub Actions, configure `MULTIREPO_READ_TOKEN` com acesso somente leitura aos 12 repositórios. O workflow roda manualmente e semanalmente.

## 12. Backup e restore

```bash
scripts/backup-local.sh
```

Restore de PostgreSQL/MongoDB é destrutivo e exige consentimento explícito:

```bash
ALLOW_DESTRUCTIVE_RESTORE=true \
  scripts/restore-local.sh backups/<timestamp>
```

Consulte `docs/operations/disaster-recovery.md`.

## 13. Carga e caos

```bash
docker run --rm --network host \
  -e BASE_URL=http://localhost:5153 \
  -v "$PWD/tests/load:/tests:ro" \
  grafana/k6:2.0.0 run /tests/readiness.js
```

Chaos drill local:

```bash
ALLOW_DESTRUCTIVE_DRILL=true \
  scripts/chaos-drill.sh conversation-memory-service
```

Consulte `docs/testing/load-and-chaos.md`.

## 14. LGPD e retenção

A matriz técnica inicial está em `docs/governance/data-retention-lgpd.md`. Os prazos são referência e precisam de aprovação de Jurídico/LGPD/Negócio.

## 15. Reset

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml down
```

Reset completo:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml down -v
```

## 16. Limitações restantes

- `core-bancario-mock` ainda não valida JWT/tenant/idempotência e não possui health dedicado;
- HS256 por par ainda é identidade simétrica sem rotação automatizada;
- Handoff não integra plataforma humana real;
- receiver de Alertmanager é local/nulo;
- Kafka, OpenSearch e rede continuam em configuração local;
- assinatura/atestado de imagens deve ser implementada em cada repositório de serviço;
- retenção, exclusão e criptografia gerenciada dependem de implementação e aprovação corporativas;
- restore de Kafka/OpenSearch continua baseado em reconstrução/replay;
- E2E multi-repositório depende do secret `MULTIREPO_READ_TOKEN`.

## 17. Troubleshooting

### Compose exige segredo

Execute `scripts/write-ci-env.sh` para placeholders de CI ou preencha `.env` com valores locais.

### Kafka init falha

Mantenha o loop de criação de tópicos como bloco shell único e valide com:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml config
```

### Regra Prometheus não carrega

```bash
docker run --rm --entrypoint /bin/promtool \
  -v "$PWD/config/prometheus:/etc/prometheus:ro" \
  prom/prometheus:v2.53.1 \
  check config /etc/prometheus/prometheus.yml
```
