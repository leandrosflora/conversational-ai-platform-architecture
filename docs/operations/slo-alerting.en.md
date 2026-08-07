# SLOs and Operational Alerts

## Scope

The local stack loads Prometheus rules and Alertmanager. This creates an executable baseline for homologation; it does not replace enterprise incident management, escalation, and on-call definitions.

## Proposed SLOs

| Journey/capability | SLI | Initial objective | Window |
|---|---|---:|---:|
| Webhook reception | proportion of `2xx` responses after Kafka persistence | 99.9% | 30 days |
| Orchestrator processing | messages completed without `failed` | 99.5% | 30 days |
| Outbox publishing | effects published within 5 minutes | 99.0% | 30 days |
| Governed tool | authorized calls completed without technical error | 99.5% | 30 days |
| RAG search | queries completed in under 2 seconds | 95% | 7 days |
| Observable infrastructure | critical targets available | 99.9% | 30 days |

These objectives are an engineering baseline. Production should adjust them using real volume, journey criticality, and an approved error budget.

## Versioned rules

Rules are stored in `config/prometheus/rules/platform-alerts.yml` and cover:

- Prometheus, Jaeger, Alloy, and Alertmanager unavailability;
- rule-evaluation failures;
- DLQ traffic;
- processing and Outbox failures;
- growth in late messages;
- internal authentication failures;
- tool-policy denials.

Missing metrics do not generate alerts. Each service must expose the documented series for the corresponding rule to become active.

## Local Alertmanager

The `local-null` receiver prevents accidental notifications in development. In homologation/production, replace it with approved integrations while preserving:

- grouping by `alertname`, `service`, and `severity`;
- shorter repeat intervals for critical alerts;
- inhibition of equivalent warnings while a critical alert is active;
- ownership and escalation routes by service.

## Validation

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

The smoke test also confirms that Prometheus loaded the rule groups and discovered Alertmanager.
