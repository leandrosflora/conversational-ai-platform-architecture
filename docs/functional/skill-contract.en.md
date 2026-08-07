# Functional Skill Contract

## Objective

A skill is a versioned functional unit with an owner, capabilities, state, tools, assurance level, and indicators. The executable catalog is in `contracts/functional/skills.yaml`.

## Required fields

| Field | Purpose |
|---|---|
| `id` and `version` | Identity and compatibility |
| `owner` and `domain` | Functional responsibility |
| `runtimeService` | Currently registered implementation |
| `operationMode` | `read_only` or `transactional` |
| `requiredAssuranceLevel` | Minimum level required to expose data |
| `stepUpOperations` | Operations that require additional authentication |
| `supportedIntents` | Functional boundary of the skill |
| `capabilities` | Capabilities implemented by the skill |
| `tools` | Tools and their mutability |
| `initialState` and `terminalStates` | Journey contract |
| `outOfScopeStrategy` | Out-of-scope behavior |
| `handoffReasons` | Controlled vocabulary |
| `dataClassification` | Data sensitivity |
| `kpis` | Associated indicators |

## Rules

1. A mutable tool can only belong to a `transactional` skill.
2. Formalization operations must require explicit confirmation and may require step-up authentication.
3. A skill cannot call services outside the catalog.
4. The Orchestrator routes by `skill.id` but does not interpret the skill's state fields.
5. An incompatible change to intents, tools, or states requires a version increment.
6. An out-of-scope request returns to the menu or requests handoff according to the catalog.

## Current skills

### Renegotiation

Transactional skill that owns the recovery journey. It requires verified identity and has a step-up operation for agreement confirmation.

### Card

Read-only skill for limit and invoice inquiries. Renegotiation questions or other operations return to the menu.

## Adding a new skill

A new skill can only be registered when it has:

- an owner and domain;
- an intent catalog;
- a state contract;
- authorized tools;
- identity criteria;
- business events;
- handoff reasons;
- functional evals;
- KPIs and SLOs;
- exception documentation.
