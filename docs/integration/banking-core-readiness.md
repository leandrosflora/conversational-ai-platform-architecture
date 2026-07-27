# P10 — Banking Core Integration Readiness

## Objetivo

Preparar a substituição segura do `core-bancario-mock` por APIs reais e governadas dos domínios bancários, sem acoplar agentes, jornadas e contratos funcionais aos payloads de sistemas legados.

## Arquitetura

```text
Agent / Tool Service
        ↓
Serviço de domínio
        ↓
Porta funcional canônica
        ↓
Adapter selecionado por ambiente
        ↓
Mock | Sandbox | API bancária real
```

## Princípios

1. Agentes não acessam o Core diretamente.
2. Serviços de domínio permanecem responsáveis por validações financeiras.
3. Adapters convertem payloads externos em modelos canônicos.
4. O provider é selecionado por perfil de deployment, não por lógica do agente.
5. Produção não aceita `mock`, dados sintéticos ou provider sem certificação.
6. Operações mutáveis exigem idempotência persistente, auditoria e reconciliação.

## Perfis

| Ambiente | Provider | Dados | Efeito financeiro |
|---|---|---|---|
| Local | Mock | Sintéticos | Nenhum |
| Demo | Mock | Sintéticos | Nenhum |
| Homologação | Sandbox | Mascarados | Simulado |
| Produção | APIs reais | Confidenciais | Transacional |

A fonte executável é `contracts/banking/integration-profiles.yaml`.

## Portas funcionais

- identificação de cliente;
- carteira de dívidas;
- elegibilidade;
- simulação de proposta;
- formalização de acordo;
- atendimento de cartão.

Cada porta possui provider mock, equivalente produtivo, owner, consumidor e natureza da operação em `contracts/banking/ports.yaml`.

## Modelos canônicos

Os serviços usam modelos independentes de produtos e plataformas específicas, incluindo:

- `CustomerReference`;
- `DebtContract`;
- `EligibilityDecision`;
- `NegotiationOffer`;
- `Agreement`;
- `CardLimit`;
- `CardInvoice`.

Valores financeiros sempre incluem moeda e data de referência.

## Evidências

As validações são classificadas como:

| Evidência | Situação atual |
|---|---|
| Integração técnica E2E | Implementada com mock |
| Estado e controle da jornada | Implementados |
| Segurança entre workloads | Baseline implementado |
| Regra financeira real | Não comprovada pelo mock |
| Contrato com Core produtivo | Pendente |
| Reconciliação financeira | Pendente |
| Certificação do produto | Pendente |

## Critério de produção

Uma release de produção é bloqueada quando:

- qualquer provider é `core-bancario-mock`;
- `providerMode` não é `real`;
- há dados classificados como sintéticos;
- falta certificação de contrato;
- falta idempotência persistente para operação mutável;
- falta reconciliação da formalização.
