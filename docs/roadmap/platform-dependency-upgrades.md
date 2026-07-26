# Plano de atualização de Kafka, Jaeger e Loki

## Objetivo

Retirar versões arquivadas ou antigas sem misturar a atualização de três componentes críticos no mesmo change set. Cada etapa deve preservar o ambiente local, o smoke test do CI e as evidências E2E da jornada.

## Baseline

| Componente | Versão atual | Linha alvo | Prioridade | Motivo |
|---|---:|---:|---|---|
| Kafka | `3.9.2` | `4.3.x` | Alta | A linha 3.9 foi arquivada; a migração exige validação de clientes e configuração KRaft |
| Jaeger | `1.60` all-in-one | `2.x` | Alta | A linha 1.x está arquivada e o modelo de configuração do Jaeger 2 mudou |
| Loki | `2.9.8` | `3.7.x` | Alta | A linha 3.x é a corrente e deve ser validada com schema TSDB e Grafana Alloy |
| Grafana Alloy | `1.16.1` | Atualização contínua controlada | Média | Substitui Promtail e passa a ser o collector padrão |

## Estratégia

### Fase 0 — Baseline e proteção

- Manter `scripts/ci-smoke.sh` verde.
- Registrar tempo de subida, uso de memória e endpoints de saúde.
- Confirmar os nove tópicos Kafka, labels no Loki, datasource do Jaeger e target do Alloy no Prometheus.
- Preservar volumes locais antes de qualquer teste destrutivo.

**Saída:** baseline reproduzível e rollback documentado.

### Fase 1 — Loki 2.9.8 → 3.7.x

1. Atualizar apenas a imagem do Loki.
2. Validar `schema_config` v13 e armazenamento TSDB local.
3. Confirmar ingestão via Alloy e consultas por `{service="..."}`.
4. Executar smoke test e uma jornada E2E.
5. Validar dashboards e retenção antes de remover o volume antigo.

**Rollback:** restaurar a imagem anterior e o volume capturado antes da migração.

### Fase 2 — Jaeger 1.60 → 2.x

1. Criar arquivo de configuração explícito para Jaeger 2.
2. Migrar a imagem `jaegertracing/all-in-one` para `jaegertracing/jaeger`.
3. Preservar OTLP gRPC `4317`, OTLP HTTP `4318` e UI `16686`.
4. Ajustar o endpoint de métricas usado pelo Prometheus.
5. Confirmar traces dos serviços .NET e Python e o datasource do Grafana.

**Rollback:** retornar ao all-in-one 1.x enquanto o formato de configuração 2.x estiver em homologação.

### Fase 3 — Kafka 3.9.2 → 4.3.x

1. Inventariar versões das bibliotecas cliente em todos os repositórios.
2. Executar testes de compatibilidade produtor/consumidor antes de trocar o broker.
3. Revisar configurações KRaft removidas, alteradas ou depreciadas.
4. Atualizar `kafka` e `kafka-init` juntos.
5. Validar criação dos nove tópicos, retry, DLQ, commits de offset e comportamento do Inbox/Outbox.
6. Executar jornada E2E com falha induzida no Orchestrator para confirmar retry e redelivery.

**Rollback:** restaurar imagem e volume do broker; não reutilizar volume convertido sem teste de downgrade.

## Critérios de aceite por fase

- `docker compose config --quiet` sem erro.
- `mkdocs build --strict` sem links inválidos.
- `scripts/ci-smoke.sh` verde.
- Nenhum tópico, porta ou datasource removido sem substituição documentada.
- Jornada E2E principal concluída.
- Evidência adicionada em `docs/validation/`.
- Rollback executado pelo menos uma vez em ambiente descartável.

## Ordem recomendada

```text
Alloy (concluído)
  → Loki
  → Jaeger
  → Kafka
```

Loki vem primeiro porque já recebe logs pelo Alloy. Jaeger vem depois por exigir uma mudança de configuração maior. Kafka fica por último porque afeta durabilidade, retry, DLQ e o caminho crítico de entrada.
