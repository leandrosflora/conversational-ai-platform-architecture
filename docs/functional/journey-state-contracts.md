# Contratos de estado das jornadas

## Objetivo

Validar deterministicamente o estado que cada Agent Runtime devolve. A fonte executável está em `contracts/functional/journeys.yaml`.

## Estrutura

Cada jornada declara:

- versão do schema;
- estado inicial;
- estados conhecidos;
- campos obrigatórios por estado;
- transições válidas;
- evento funcional da transição;
- invariantes.

## Renegociação

```text
Started
  → CustomerIdentified
  → ContractSelectionPending ─┐
  → ContractSelected ◀────────┘
  → EligibilityChecked
  → ProposalAvailable
  → ProposalSelected
  → AgreementConfirmed
  → DocumentAvailable
```

`HandoffRequested` é uma saída controlada possível antes do encerramento.

### Invariantes

- transições são progressivas, exceto reset de sessão;
- identificadores financeiros não podem ser derivados de CPF parcial;
- operação mutável exige confirmação explícita;
- o estado persistido deve conter os campos obrigatórios do estágio;
- proposta deve possuir validade;
- documento só pode existir após acordo confirmado.

## Cartão

```text
Started
  → CustomerIdentified
  ↺ CardInformationDelivered
  → ReturnedToMenu
  → HandoffRequested
```

A consulta não cria um estágio transacional permanente. O CPF verificado permanece no `structured_state` durante a sessão.

## Compatibilidade

- inclusão de campo opcional: mudança compatível;
- novo estado alcançável sem alterar estados existentes: minor version;
- remoção ou renome de estado/campo obrigatório: major version;
- o Orchestrator deve persistir `stateSchemaVersion` junto ao estado;
- migração deve ser definida antes de alterar uma jornada com conversas ativas.
