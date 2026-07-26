# SLOs e alertas operacionais

## Escopo

O stack local passa a carregar regras Prometheus e Alertmanager. Isso cria um baseline executável para homologação; não substitui a definição corporativa de incidentes, escalonamento e plantão.

## SLOs propostos

| Jornada/capacidade | SLI | Objetivo inicial | Janela |
|---|---|---:|---:|
| Recepção de webhook | proporção de respostas `2xx` após persistência no Kafka | 99,9% | 30 dias |
| Processamento do Orchestrator | mensagens concluídas sem `failed` | 99,5% | 30 dias |
| Publicação da Outbox | efeitos publicados em até 5 minutos | 99,0% | 30 dias |
| Tool governada | chamadas autorizadas concluídas sem erro técnico | 99,5% | 30 dias |
| Busca RAG | consultas concluídas em menos de 2 segundos | 95% | 7 dias |
| Infraestrutura observável | targets críticos disponíveis | 99,9% | 30 dias |

Os objetivos são baseline de engenharia. Produção deve ajustá-los com volume real, criticidade da jornada e orçamento de erro aprovado.

## Regras versionadas

As regras ficam em `config/prometheus/rules/platform-alerts.yml` e cobrem:

- indisponibilidade de Prometheus, Jaeger, Alloy e Alertmanager;
- falhas de avaliação de regras;
- tráfego em DLQ;
- falhas de processamento e Outbox;
- crescimento de mensagens atrasadas;
- falhas de autenticação interna;
- negações de policy de tools.

Métricas ausentes não geram alerta. Cada serviço precisa expor as séries documentadas para que a regra correspondente se torne ativa.

## Alertmanager local

O receiver `local-null` evita envio acidental de notificações em desenvolvimento. Em homologação/produção, substituir por integrações aprovadas, mantendo:

- agrupamento por `alertname`, `service` e `severity`;
- repetição mais curta para alertas críticos;
- inibição de warnings equivalentes quando há critical ativo;
- ownership e rota de escalonamento por serviço.

## Validação

```bash
docker run --rm --entrypoint /bin/promtool \
  -v "$PWD/config/prometheus:/etc/prometheus:ro" \
  prom/prometheus:v2.53.1 \
  check config /etc/prometheus/prometheus.yml

docker run --rm --entrypoint /bin/amtool \
  -v "$PWD/config/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" \
  prom/alertmanager:v0.32.1 \
  check-config /etc/alertmanager/alertmanager.yml
```

O smoke test também confirma que o Prometheus carregou os grupos de regras e descobriu o Alertmanager.
