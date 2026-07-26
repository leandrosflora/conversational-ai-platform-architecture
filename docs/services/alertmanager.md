# alertmanager

Origem: provisionado por este repositório · Imagem: `prom/alertmanager:v0.32.1` · Porta local: `9093`

## Responsabilidade

Receber alertas do Prometheus, agrupar ocorrências correlatas, aplicar regras de inibição e encaminhar notificações aos receivers configurados.

## Estado implementado

- configuração versionada em `config/alertmanager/alertmanager.yml`;
- receiver local `local-null`, sem envio externo;
- agrupamento por `alertname`, `service` e `severity`;
- repetição mais curta para alertas críticos;
- inibição de warning equivalente quando um critical está ativo;
- storage persistente local `alertmanager-data`;
- readiness em `GET /-/ready`;
- API/UI em `http://localhost:9093`.

## Dependências

| Origem | Integração |
|---|---|
| Prometheus | envia alertas para `alertmanager:9093` |
| Operador local | consulta UI/API na porta `9093` |

## Limitações

O receiver nulo é uma proteção para desenvolvimento. Homologação e produção precisam de receivers aprovados, ownership por serviço, escalonamento, plantão e testes periódicos de entrega.

## Referências

- [SLOs e alertas](../operations/slo-alerting.md)
- [Runbook](../runbook.md)
