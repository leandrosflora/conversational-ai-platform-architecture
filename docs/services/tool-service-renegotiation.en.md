# tool-service-renegotiation

Repo: [`leandrosflora/tool-service-renegotiation`](https://github.com/leandrosflora/tool-service-renegotiation) · Stack: Python, MCP (FastMCP) + FastAPI, Confluent.Kafka · Local ports: `8400` (MCP), `8401` (REST mirror)

## Primary responsibility

MCP server that exposes renegotiation-flow operations as governed tools. It translates each tool call into an HTTP request to `renegotiation-service` and publishes a `tool.executed` audit event for every execution, whether successful or not.

## Data owned by the service

None — it is a thin translation layer between the MCP protocol and `renegotiation-service`, with no domain model of its own.

## Published APIs

Streamable-HTTP MCP server at `/mcp` on port `8400`, **plus a complete REST mirror** of the same seven operations on port `8401` (the same routes as `renegotiation-service`, for example `GET /clients/{cpf}`, `POST /contracts/{contractId}/simulations`) — signed execution context is also mandatory on this path. Seven MCP tools are exposed:

| Tool | Parameters | Called HTTP endpoint |
|---|---|---|
| `consultar_cliente` | `cpf` | `GET /clients/{cpf}` |
| `consultar_contratos` | `client_id` | `GET /clients/{client_id}/contracts` |
| `consultar_debitos` | `contract_id` | `GET /contracts/{contract_id}/debts` |
| `validar_elegibilidade` | `contract_id` | `GET /contracts/{contract_id}/eligibility` |
| `simular_proposta` | `contract_id, installments, discount_percentage=0.0` | `POST /contracts/{contract_id}/simulations` |
| `confirmar_acordo` | `simulation_id` | `POST /simulations/{simulation_id}/confirmations` |
| `gerar_documento` | `agreement_id` | `GET /agreements/{agreement_id}/document` |

## Published events

| Topic | When | Payload |
|---|---|---|
| `tool.executed` | Always, in `finally`, after every tool call (success or error) | `tool_name`, `outcome` (`"success"`\|`"error"`), `correlation_id` |

**Important:** the payload never includes tool arguments (tax ID, contract/simulation/agreement IDs). This is not masking; it is complete omission by design, so no raw sensitive identifier can leak into the audit trail. Publish failures are swallowed using catch-log-continue behavior.

## Consumed events

None.

## Synchronous dependencies

| Destination | Behavior when unavailable |
|---|---|
| `renegotiation-service` (`:9400`) | 5-second timeout per call; retries through `tenacity` (2 additional attempts = 3 total, 0.2s apart). If all attempts fail, raises `RenegotiationServiceUnavailableError` **without** the original error message to avoid leaking URL/tax-ID details into logs. The exception propagates and FastMCP converts it to `ToolError` for the agent client |

## Persistence and infrastructure

None. The service is stateless — each tool call creates a new `httpx.AsyncClient`, with no persistent connection pool across calls.

## Business rules

1. Tool arguments, including potentially sensitive data such as tax IDs, are never published to Kafka under any circumstance.
2. Network/timeout failure while calling `renegotiation-service` is not converted into a structured successful result — it becomes an MCP exception (`ToolError`) propagated to the agent, not an `{"error": ...}` payload.
3. HTTP-client error logs record only the exception type, never the full message/URL, for the same sensitive-data protection reason.
4. **Journey-stage authorization policy** (`app/policy.py`) applies to every MCP or REST tool call through `authorize_tool`: only `agent-runtime-renegotiation` may call the service (from signed-context `caller_service`). Each read tool (`consultar_cliente`, `consultar_contratos`, `consultar_debitos`, `validar_elegibilidade`) is allowed only from a specific `journey_stage` allowlist. The allowlist deliberately includes `Started`/early stages because the stage claim is signed once per turn and does not advance mid-turn, and includes `HandoffRequested` so a conversation reopened by the bot does not become permanently blocked. `simular_proposta` requires a stage in `SIMULATION_STAGES` and all three arguments (`contract_id`, `installments`, `discount_percentage`); `gerar_documento` is allowed only from `AgreementConfirmed`/`DocumentAvailable`/`Completed`.
5. **`confirmar_acordo`** requires not only the proper stage (`ProposalSelected`/`ConfirmationPending`) but evidence of explicit confirmation: `confirmation_message_id` must be present and equal to the current `message_id`, never inherited from an earlier turn.
6. **Deterministic idempotency key**: `simular_proposta` derives its `Idempotency-Key` from a SHA-256 hash of `(tenant_id, conversation_id, message_id, journey_version, contract_id, installments, discount_percentage)`; `confirmar_acordo` derives its key from `(tenant_id, conversation_id, confirmation_message_id, simulation_id)`. Both are forwarded to `renegotiation-service`, which provides the actual idempotency guarantee (see [renegotiation-service](renegotiation-service.md)).

## Architecture references

- [ADR 0003 — MCP for governed tool calling](../adr/0003-mcp-governed-tool-calling.md)
- [Security architecture](../security/security-architecture.md)
- [Journey sequence diagrams](../architecture/sequence-diagrams.md)
