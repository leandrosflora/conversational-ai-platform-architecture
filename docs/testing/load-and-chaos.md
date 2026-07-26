# Testes de carga e caos

## Carga

`tests/load/readiness.js` usa k6 com taxa constante e thresholds explícitos:

```bash
docker run --rm --network host \
  -e BASE_URL=http://localhost:5153 \
  -v "$PWD/tests/load:/tests:ro" \
  grafana/k6:2.0.0 run /tests/readiness.js
```

Baseline:

- 10 requisições por segundo durante 30 segundos;
- menos de 1% de falhas;
- `p95` abaixo de 500 ms;
- mais de 99% dos checks aprovados.

O teste de readiness verifica capacidade básica. Produção precisa de cenários de webhook, Orchestrator, RAG e tools com dados sintéticos e limites por tenant.

## Caos controlado

`scripts/chaos-drill.sh` pausa temporariamente apenas serviços allowlisted e restaura o container ao sair.

```bash
ALLOW_DESTRUCTIVE_DRILL=true \
  PAUSE_SECONDS=20 \
  scripts/chaos-drill.sh conversation-memory-service
```

Não execute contra ambientes compartilhados ou produção.

## Cenários recomendados

- Memory, Audit ou Handoff indisponível durante publicação da Outbox;
- Renegotiation Service indisponível durante simulação;
- OpenSearch lento ou indisponível;
- reinício do Orchestrator com lease ativo;
- indisponibilidade temporária de Kafka;
- erro/timeout do provedor de modelo;
- retorno do downstream e replay sem duplicação.

## Critérios de aceite

- nenhuma mensagem aceita é perdida;
- Outbox/Retry/DLQ refletem a falha;
- versões posteriores não ultrapassam efeitos anteriores;
- recuperação não duplica side effects;
- alertas correspondentes ficam visíveis;
- o relatório inclui timestamps, commits, logs e estado dos datastores.
