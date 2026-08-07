# core-bancario-mock

Repo: [`leandrosflora/core-bancario-mock`](https://github.com/leandrosflora/core-bancario-mock) · Stack: .NET 8, Minimal API, single process · Local ports: `9401`–`9405`

!!! danger "Demonstration and homologation only"
    This service does not represent a production Banking Core and contains no real data. All customers, contracts, debts, proposals, agreements, limits, and invoices are synthetic. No response from this service should be interpreted as valid financial information, and no confirmation creates a real obligation, contract, or posting.

## Responsibility

Mock of the external banking APIs used by the renegotiation and card journeys. Renegotiation APIs are consumed through `renegotiation-service`; Card API is consumed directly by `tool-service-cartao-credito`.

Its purpose is to enable deterministic testing of:

- API contracts;
- workload authentication and authorization;
- tenant isolation;
- idempotency;
- journey states;
- error handling;
- observability and multi-repository E2E.

It does not validate enterprise financial rules, production-data quality, or adherence to real banking products.

## APIs

| Port | API | Endpoints |
|---|---|---|
| `9401` | ClientApi | `GET /clients/{cpf}` · `GET /clients/{clientId}/contracts` · `GET /contracts/{contractId}/debts` |
| `9402` | EligibilityApi | `GET /contracts/{contractId}/eligibility` |
| `9403` | ContractingApi | `POST /contracts/{contractId}/simulations` |
| `9404` | FormalizationApi | `POST /simulations/{simulationId}/confirmations` · `GET /agreements/{agreementId}/document` |
| `9405` | CardApi | `GET /clients/{cpf}/card/limit` · `GET /clients/{cpf}/card/invoice` |

Health and metrics:

```text
GET /health/live
GET /health/ready
GET /metrics
```

## Target architecture

In an enterprise deployment, each endpoint group must be replaced by real APIs from the responsible systems:

| Current mock | Expected target-architecture destination |
|---|---|
| ClientApi | Authorized customer registry and customer view |
| Contracts and debts | Contracts, collections, or recovery system |
| EligibilityApi | Enterprise eligibility/policy engine |
| ContractingApi | Simulation and financial-terms engine |
| FormalizationApi | Contracting, formalization, and document management |
| CardApi | Real card processor or card-domain platform |

Replacement must not be a simple URL change. It must include versioned contracts, workload authentication, operation-level authorization, persistent idempotency, concurrency handling, SLA, auditability, data classification, and homologation using non-production datasets.

## Authentication in the integrated environment

Compose enables fail-closed authentication in the Core:

- HS256 with a distinct secret per caller/audience pair;
- key resolution through `kid`;
- `kid == sub`;
- validation of `iss`, `aud`, algorithm, expiration, and signature;
- signed `tenant_id` must be a UUID and equal `X-Tenant-Id`;
- renegotiation APIs accept only `renegotiation-service`;
- Card API accepts only `tool-service-cartao-credito`.

Health and metrics are public. When running this repository in isolation, authentication remains disabled by default and must be explicitly enabled.

## Idempotency

Mutable operations require `Idempotency-Key`:

- simulation;
- confirmation.

With the same key and request, the service returns exactly the stored response. The same key with a different request returns non-retryable `409`; concurrent execution returns retryable `409`.

The mock store is in memory and is lost on restart. `renegotiation-service` maintains its own durable PostgreSQL idempotency, so the Core adds defense in depth for homologation but does not replace persistence in the real banking system.

## CI and tests

The repository runs restore, build, and integration tests. The suite covers:

- live/readiness;
- missing token;
- allowed and denied caller by API;
- tenant mismatch;
- simulation and confirmation replay;
- payload conflict;
- missing idempotency key.

These tests prove technical behavior of the mock and its consumers. They do not prove financial calculations, production eligibility, real balances, or real banking formalization.

## Data

Reserved tax IDs provide deterministic scenarios. There is no real database. IDs and idempotent replay exist only for the lifetime of the process.

Data characteristics:

- fully synthetic;
- no relationship to real people;
- no production-environment origin;
- values generated for test scenarios;
- suitable only for development, demonstration, CI, and technical homologation.

## Limitations

- process-local idempotency with no persistence after restart;
- symmetric HS256 with no automated rotation;
- no journey-stage policy proof for Card API because operations are read-only;
- no real banking datastore;
- simulation values still start from a fixed test baseline;
- simplified eligibility and contracting rules;
- no reconciliation, accounting, settlement, or payment confirmation;
- unavailable for any production use.

## References

- [Business context](../context/business-context.md)
- [Domain map](../functional/domain-map.md)
- [Security architecture](../security/security-architecture.md)
- [Production roadmap](../roadmap/production-readiness.md)
- [Multi-repository E2E](../runbook.md#11-e2e-multi-repositório)
