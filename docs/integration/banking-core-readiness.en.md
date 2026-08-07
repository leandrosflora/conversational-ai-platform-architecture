# P10 — Banking Core Integration Readiness

## Objective

Prepare the safe replacement of `core-bancario-mock` with real, governed APIs from banking domains without coupling agents, journeys, and functional contracts to legacy-system payloads.

## Architecture

```text
Agent / Tool Service
        ↓
Domain service
        ↓
Canonical functional port
        ↓
Environment-selected adapter
        ↓
Mock | Sandbox | Real banking API
```

## Principles

1. Agents do not access the Core directly.
2. Domain services remain responsible for financial validations.
3. Adapters convert external payloads into canonical models.
4. The provider is selected by deployment profile, not by agent logic.
5. Production does not accept `mock`, synthetic data, or uncertified providers.
6. Mutable operations require persistent idempotency, auditability, and reconciliation.

## Profiles

| Environment | Provider | Data | Financial effect |
|---|---|---|---|
| Local | Mock | Synthetic | None |
| Demo | Mock | Synthetic | None |
| Homologation | Sandbox | Masked | Simulated |
| Production | Real APIs | Confidential | Transactional |

The executable source is `contracts/banking/integration-profiles.yaml`.

## Functional ports

- customer identification;
- debt portfolio;
- eligibility;
- offer simulation;
- agreement formalization;
- card servicing.

Each port has a mock provider, production equivalent, owner, consumer, and operation nature in `contracts/banking/ports.yaml`.

## Canonical models

Services use models independent of specific products and platforms, including:

- `CustomerReference`;
- `DebtContract`;
- `EligibilityDecision`;
- `NegotiationOffer`;
- `Agreement`;
- `CardLimit`;
- `CardInvoice`.

Financial values always include currency and reference date.

## Evidence

Validations are classified as:

| Evidence | Current status |
|---|---|
| Technical E2E integration | Implemented with mock |
| Journey state and control | Implemented |
| Workload-to-workload security | Baseline implemented |
| Real financial rule | Not proven by the mock |
| Production Core contract | Pending |
| Financial reconciliation | Pending |
| Product certification | Pending |

## Production criterion

A production release is blocked when:

- any provider is `core-bancario-mock`;
- `providerMode` is not `real`;
- data is classified as synthetic;
- contract certification is missing;
- persistent idempotency is missing for a mutable operation;
- formalization reconciliation is missing.
