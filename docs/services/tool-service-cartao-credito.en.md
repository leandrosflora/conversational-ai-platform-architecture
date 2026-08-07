# tool-service-cartao-credito

Repo: [`leandrosflora/tool-service-cartao-credito`](https://github.com/leandrosflora/tool-service-cartao-credito) · Stack: Python, MCP (FastMCP) + FastAPI, Confluent.Kafka · Local ports: `8410` (MCP), `8411` (REST/docs)

## Primary responsibility

Thin MCP server for the credit-card invoice/limit skill, consumed by `agent-runtime-fatura-cartao`. It exposes two governed, read-only MCP tools that translate each call directly into an HTTP request to `core-bancario-mock` (Card API, `:9405`) and publish a `tool.executed` audit event for every execution. It is deliberately simpler than `tool-service-renegotiation`: because both tools are stateless read operations with no multi-step journey or irreversible action, there is no intermediate business service or journey-stage gate — authorization policy checks only *which service* may call the tools.

## Data owned by the service

None — it is a thin translation layer between MCP and `core-bancario-mock`, with no domain model of its own.

## Published APIs

Streamable-HTTP MCP server at `/mcp` on port `8410`. Two tools are exposed:

| Tool | Parameters | Called HTTP endpoint |
|---|---|---|
| `consultar_limite_cartao` | `cpf` | `GET {CORE_BANCARIO_BASE_URL}/clients/{cpf}/card/limit` |
| `consultar_fatura_cartao` | `cpf` | `GET {CORE_BANCARIO_BASE_URL}/clients/{cpf}/card/invoice` |

Both return a fixed not-found shape (`found: false`) when the tax ID resolves to no customer. This differs from `HasCard: false`, which represents a real customer without a card product and is reported by `core-bancario-mock`, allowing the agent to distinguish both situations in conversation.

A REST mirror is also available on port `8411`, with mandatory signed execution context, exposing the same two routes (`GET /clients/{cpf}/card/limit`, `GET /clients/{cpf}/card/invoice`) plus `GET /health/live`, `GET /health/ready`, and `GET /metrics`.

## Published events

| Topic | When | Payload |
|---|---|---|
| `tool.executed` | Always, after each tool call (success or error) | `tenant_id`, `tool_name`, `outcome` (`"success"`\|`"error"`), `correlation_id` |

The payload never includes the tax ID or other tool arguments — the same redaction-by-omission practice used by `tool-service-renegotiation` to prevent sensitive data from leaking into the audit topic. Publish failures are swallowed through catch-log-continue behavior.

## Consumed events

None.

## Synchronous dependencies

| Destination | Behavior when unavailable |
|---|---|
| `core-bancario-mock` (`:9405`) | Direct HTTP call with a signed JWT (`Authorization: Bearer` + `X-Tenant-Id`, audience `core-bancario-mock`) attached for platform consistency — but **not validated on the other side** in the service version described here. Timeout is 5 seconds per call; retries through `tenacity` (2 additional attempts = 3 total, 0.2s apart). A `404` for an unknown tax ID is treated as a normal business result and is not retried; it returns the not-found shape. Any other failure after all attempts raises `CoreBancarioUnavailableError`, propagated to the agent client |

## Persistence and infrastructure

None. The service is stateless — every tool call directly translates into an HTTP request to `core-bancario-mock`.

## Business rules

1. **Authorization by caller service**: only `agent-runtime-fatura-cartao` may execute the governed tools (`consultar_limite_cartao`, `consultar_fatura_cartao`), verified through `caller_service` in the signed execution context; any other caller receives a policy-denied error.
2. **Signed execution context required**: the JWT must have `token_use == "tool_execution"` plus `sub`, `conversation_id`, and `message_id`; otherwise the request returns `403`.
3. Tool arguments, including tax IDs, are never published to Kafka under any circumstance.
4. The call to `core-bancario-mock` uses its own outbound secret (`INTERNAL_AUTH_SECRET_TOOL_SERVICE_CARTAO_CREDITO__CORE_BANCARIO_MOCK`) and signs a JWT with it. In the implementation version documented here, the mock does not validate that token, so this is structural parity rather than an effective security control; see [`docs/security/security-architecture.md`](../security/security-architecture.md).

## Architecture references

- [ADR 0003 — MCP for governed tool calling](../adr/0003-mcp-governed-tool-calling.md)
- [Security architecture](../security/security-architecture.md)
- [Journey sequence diagrams](../architecture/sequence-diagrams.md)
