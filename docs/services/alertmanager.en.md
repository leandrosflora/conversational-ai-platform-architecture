# alertmanager

Source: provisioned by this repository · Image: `prom/alertmanager:v0.32.1` · Local port: `9093`

## Responsibility

Receive alerts from Prometheus, group correlated occurrences, apply inhibition rules, and route notifications to configured receivers.

## Implemented state

- versioned configuration in `config/alertmanager/alertmanager.yml`;
- local `local-null` receiver with no external delivery;
- grouping by `alertname`, `service`, and `severity`;
- shorter repeat interval for critical alerts;
- inhibition of an equivalent warning while a critical alert is active;
- persistent local storage `alertmanager-data`;
- readiness at `GET /-/ready`;
- API/UI at `http://localhost:9093`.

## Dependencies

| Source | Integration |
|---|---|
| Prometheus | sends alerts to `alertmanager:9093` |
| Local operator | accesses UI/API on port `9093` |

## Limitations

The null receiver is a development safeguard. Homologation and production require approved receivers, ownership by service, escalation, on-call coverage, and periodic delivery tests.

## References

- [SLOs and alerts](../operations/slo-alerting.md)
- [Runbook](../runbook.md)
