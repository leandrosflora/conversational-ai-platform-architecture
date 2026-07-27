# Contrato funcional de skill

## Objetivo

Uma skill é uma unidade funcional versionada, com owner, capacidades, estado, tools, nível de garantia e indicadores. O catálogo executável está em [`contracts/functional/skills.yaml`](../../contracts/functional/skills.yaml).

## Campos obrigatórios

| Campo | Finalidade |
|---|---|
| `id` e `version` | Identidade e compatibilidade |
| `owner` e `domain` | Responsabilidade funcional |
| `runtimeService` | Implementação atualmente registrada |
| `operationMode` | `read_only` ou `transactional` |
| `requiredAssuranceLevel` | Nível mínimo para expor dados |
| `stepUpOperations` | Operações que exigem autenticação adicional |
| `supportedIntents` | Limite funcional da skill |
| `capabilities` | Capacidades que a skill implementa |
| `tools` | Ferramentas e natureza mutável |
| `initialState` e `terminalStates` | Contrato de jornada |
| `outOfScopeStrategy` | Comportamento fora de escopo |
| `handoffReasons` | Vocabulário controlado |
| `dataClassification` | Sensibilidade dos dados |
| `kpis` | Indicadores associados |

## Regras

1. Uma tool mutável só pode pertencer a skill `transactional`.
2. Operações de formalização devem exigir confirmação explícita e podem exigir step-up.
3. A skill não pode chamar serviços fora do catálogo.
4. O Orchestrator roteia por `skill.id`, mas não interpreta seus campos de estado.
5. Mudança incompatível em intents, tools ou estados exige incremento de versão.
6. Skill fora de escopo retorna ao menu ou solicita handoff conforme o catálogo.

## Skills atuais

### Renegociação

Skill transacional, dona da jornada de recuperação. Exige identidade verificada e possui operação de step-up para confirmação de acordo.

### Cartão

Skill somente leitura para limite e fatura. Perguntas de renegociação ou outras operações retornam ao menu.

## Inclusão de nova skill

Uma nova skill só pode ser registrada quando possuir:

- owner e domínio;
- catálogo de intents;
- contrato de estado;
- tools autorizadas;
- critérios de identidade;
- eventos de negócio;
- handoff reasons;
- evals funcionais;
- KPIs e SLOs;
- documentação de exceções.
