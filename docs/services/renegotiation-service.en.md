# renegotiation-service

Repo: [`leandrosflora/renegotiation-service`](https://github.com/leandrosflora/renegotiation-service) · Stack: .NET 8, Minimal API · Local port (`dotnet run`): `9400` · Host port through `docker compose up -d`: `5266`

## Primary responsibility

HTTP gateway that unifies the four Banking Core APIs mocked by `core-bancario-mock` under its own REST API: customer/contracts/debts lookup, eligibility, simulation, and formalization. It **contains no credit business rules of its own** — each use case simply calls the corresponding outbound client and passes the result through. Renegotiation business rules, such as what makes a contract ineligible or installment limits, live in `core-bancario-mock`, not here.

## Data owned by the service

Wire models (`ClientLookupResult`, `ContractsResult`, `DebtsResult`, `EligibilityResult`, `SimulationResult`, `AgreementConfirmationResult`, `DocumentResult`) are not domain data owned by the service. There is, however, one real persisted state: a PostgreSQL idempotency record per simulation through `PostgresSimulationIdempotencyStore` (see Persistence).

## Published APIs

| Method | Route | Calls (`core-bancario-mock`) |
|---|---|---|
| `GET` | `/clients/{cpf}` | ClientApi `:9401` |
| `GET` | `/clients/{clientId}/contracts` | ClientApi `:9401` |
| `GET` | `/contracts/{contractId}/debts` | ClientApi `:9401` |
| `GET` | `/contracts/{contractId}/eligibility` | EligibilityApi `:9402` |
| `POST` | `/contracts/{contractId}/simulations` | ContractingApi `:9403` |
| `POST` | `/simulations/{simulationId}/confirmations` | FormalizationApi `:9404` |
| `GET` | `/agreements/{agreementId}/document` | FormalizationApi `:9404` |

`POST /contracts/{contractId}/simulations` and `POST /simulations/{simulationId}/confirmations` require an `Idempotency-Key` header (`400` if missing) and a `governed_tool` JWT signed by `tool-service-renegotiation` (see Business rules) — `403` when signed-context validation fails. `POST /contracts/{contractId}/simulations` may also return `409 Conflict`: `retryable:true` when another simulation using the same key is still in progress, or `retryable:false` when the same key was already used with different parameters.

## Published / consumed events

None. This service does not use Kafka; it is purely synchronous HTTP request/response.

## Synchronous dependencies

The four `core-bancario-mock` APIs, each through a typed `HttpClient` with a resilience handler and two configurable retries per API.

## Persistence and infrastructure

**PostgreSQL** (`PostgresSimulationIdempotencyStore`): one row per simulation `Idempotency-Key`, storing the canonical request hash and the response received from the Banking Core. Reusing a key with the same request returns the persisted response without calling the Core again; reusing it with a different request is rejected. There is no other database — all remaining information comes from synchronous calls to the mocked Banking Core.

## Business rules

1. **Simulation idempotency**: a new `Idempotency-Key` executes the operation and persists the response; an already completed key returns the same response without calling the Banking Core again. `IdempotencyInProgressException` and `IdempotencyConflictException` distinguish a key still being processed from a key reused with different parameters.
2. **Defense-in-depth journey-stage policy**: every simulation/confirmation endpoint independently revalidates the received `governed_tool` JWT through `GovernedToolPolicy.TryAuthorize`, rather than trusting `tool-service-renegotiation` alone. It checks `sub == "tool-service-renegotiation"`, `token_use == "governed_tool"`, that `tool_name` matches the invoked operation, that all context claims (`tenant_id`, `conversation_id`, `message_id`, `journey_stage`, `journey_version`, `policy_id`) are present, that `journey_stage` belongs to the endpoint-specific allowlist mirroring the Tool Service's `SIMULATION_STAGES`/`CONFIRMATION_STAGES`, and that the `Idempotency-Key` header exactly matches the signed `policy_id` claim. Any failure returns `403`.
3. **Confirmation requires signed evidence**: `POST /simulations/{simulationId}/confirmations` additionally requires `confirmation_message_id` to be present and equal to the signed context's own `message_id`.
4. Any 2xx response from the Banking Core — even when representing a negative business outcome (`eligible:false`, `possible:false`, `confirmed:false`, `available:false`) — is passed through as `200 OK`. This is an error-mapping convention, not a credit rule; eligibility and limits belong to `core-bancario-mock`.
5. `502 Bad Gateway` is returned only when the Banking Core call genuinely fails, such as timeout or connection refusal, represented by `UpstreamServiceUnavailableException` and handled by endpoint-level `try/catch` rather than global middleware.
6. A tax ID not found in ClientApi (404) maps to `ClientLookupResult(Found: false)` because the HTTP client interprets 404 as not found. `GetContractsUseCase` and `GetDebtsUseCase` also handle that condition, but the current mock does not implement 404 for those two routes — a known gap between the client and mock; see [`docs/services/core-bancario-mock.md`](core-bancario-mock.md).

## Architecture references

- [ADR 0002 — Hexagonal / ports-and-adapters in .NET services](../adr/0002-hexagonal-ports-and-adapters.md)
- [Datastore matrix](../contracts/data-stores.md)
