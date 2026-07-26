# Runbook — Plataforma de IA Conversacional

## 1. Escopo

Este runbook descreve o estado coordenado do `main` de `conversational-ai-platform-architecture` e dos repositórios de serviço. A solução é uma referência executável/POC endurecida, não production-ready bancário.

## 2. Workspace

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

Mudanças de autenticação, tenant, contratos ou journey state exigem implantação e validação coordenadas.

## 3. Configuração

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Cada par emissor/audiência possui segredo independente. O Compose integrado habilita auth também no `core-bancario-mock`, com pares distintos para:

```text
renegotiation-service → core-bancario-mock
tool-service-cartao-credito → core-bancario-mock
```

Nunca versione valores reais.

## 4. CI

O CI deste repositório valida:

- Compose e contratos;
- Alloy, Prometheus e Alertmanager;
- scripts e documentação canônica;
- C4, MkDocs e links;
- Trivy, SARIF e SBOM;
- smoke test real da infraestrutura.

O `core-bancario-mock` executa restore, build e testes de integração de auth, health e idempotência. Os demais serviços mantêm seus próprios pipelines.

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
| core-bancario-mock | `9401`–`9405` | `/health/ready` |
| Kafka UI | `8080` | UI |
| Jaeger | `16686` | UI |
| Prometheus | `9090` | UI/API |
| Alertmanager | `9093` | UI/API |
| Grafana | `3001` | UI |
| Alloy | `12345` | `/-/ready` |

## 7. Autenticação

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

- token ausente/inválido: `401`;
- tenant ausente ou inválido: `400`;
- tenant divergente ou caller não permitido: `403`.

O Core aceita `renegotiation-service` nas APIs de renegociação e `tool-service-cartao-credito` apenas na Card API. Health e métricas permanecem públicos.

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

O `202` do Orchestrator confirma estado e efeitos registrados, não a conclusão de todos os downstreams.

O Core exige `Idempotency-Key` em simulação/confirmação e mantém replay/conflict em memória. A durabilidade principal continua no PostgreSQL do Renegotiation Service.

## 9. Kafka

```text
channel.webhook.received
channel.webhook.received.retry
channel.webhook.received.dlq
```

O offset original só é commitado após processamento ou publicação confirmada em retry/DLQ.

## 10. Observabilidade

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d \
  jaeger loki alloy alertmanager prometheus grafana
```

Prometheus carrega regras de `config/prometheus/rules/`. Alertmanager local usa receiver nulo. Consulte:

- [SLOs e alertas](operations/slo-alerting.md)
- `http://localhost:9090/alerts`
- `http://localhost:9093`
- `http://localhost:3001`

## 11. E2E multi-repositório

```bash
scripts/e2e-multirepo.sh
```

O script:

1. registra commits dos 12 serviços;
2. executa builds e testes;
3. sobe o stack completo;
4. valida readiness;
5. envia webhook Meta assinado;
6. verifica Inbox/Outbox;
7. emite JWTs temporários para testar o Core;
8. valida caller, tenant, replay e conflito idempotente;
9. coleta Kafka/Prometheus/evidências;
10. executa baseline k6.

No GitHub Actions, configure `MULTIREPO_READ_TOKEN` com leitura dos 12 repositórios. Em execução manual, `core_ref` permite validar o branch coordenado do Core antes do merge.

## 12. Backup e restore

```bash
scripts/backup-local.sh
```

```bash
ALLOW_DESTRUCTIVE_RESTORE=true \
  scripts/restore-local.sh backups/<timestamp>
```

Consulte [Backup, restore e recuperação](operations/disaster-recovery.md).

## 13. Carga e caos

```bash
docker run --rm --network host \
  -e BASE_URL=http://localhost:5153 \
  -v "$PWD/tests/load:/tests:ro" \
  grafana/k6:2.0.0 run /tests/readiness.js
```

```bash
ALLOW_DESTRUCTIVE_DRILL=true \
  scripts/chaos-drill.sh conversation-memory-service
```

Consulte [Testes de carga e caos](testing/load-and-chaos.md).

## 14. LGPD

A matriz técnica inicial está em [Retenção, classificação e LGPD](governance/data-retention-lgpd.md). Os prazos exigem aprovação de Jurídico/LGPD/Negócio.

## 15. Reset

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml down
```

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml down -v
```

## 16. Limitações

- idempotência do Core é process-local;
- HS256 por par não possui rotação/JWKS;
- Handoff não integra plataforma humana real;
- receiver do Alertmanager é local/nulo;
- Kafka, OpenSearch e rede usam configuração local;
- assinatura/atestado de imagens não está uniforme nos serviços;
- retenção, exclusão e criptografia gerenciada dependem de implementação corporativa;
- restore de Kafka/OpenSearch é baseado em reconstrução/replay;
- E2E multi-repositório depende de `MULTIREPO_READ_TOKEN`.

## 17. Troubleshooting

### Compose exige segredo

Execute `scripts/write-ci-env.sh` ou preencha todos os pares de `.env.example`.

### Core retorna `503` em readiness

Auth está habilitada e um dos segredos inbound está ausente ou possui menos de 32 bytes.

### Core retorna `401`/`403`

Verifique `kid`, `sub`, audience `core-bancario-mock`, segredo do par e igualdade entre `tenant_id` e `X-Tenant-Id`.

### Operação Core retorna `400`

Simulação e confirmação exigem `Idempotency-Key`.

### Regra Prometheus não carrega

```bash
docker run --rm --entrypoint /bin/promtool \
  -v "$PWD/config/prometheus:/etc/prometheus:ro" \
  prom/prometheus:v2.53.1 \
  check config /etc/prometheus/prometheus.yml
```
