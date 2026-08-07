# agent-runtime-fatura-cartao

Repo: [`leandrosflora/agent-runtime-fatura-cartao`](https://github.com/leandrosflora/agent-runtime-fatura-cartao) · Stack: Python, FastAPI, Strands Agents, OpenAI · Local port: `8110`

## Primary responsibility

Hosts the AI agent (Strands Agents + OpenAI) that answers customer questions about credit cards through WhatsApp: total limit, available limit, and current invoice amount. It receives a message from the Orchestrator through `POST /process`, connects to `tool-service-cartao-credito` through MCP, constructs the agent, and invokes it. It is deliberately simpler than `agent-runtime-renegotiation`: there is no multi-stage journey with contracts/simulations/agreements — only customer identification by tax ID followed by read-only queries.

## Data owned by the service

No persisted model — `ProcessRequest`/`ProcessResponse` (Pydantic, `app/models.py`) are wire contracts. The only state, the already identified tax ID, is opaque and travels in `StructuredState` exchanged with `conversation-orchestrator`; it is not persisted in the service's own database or cache.

## Published APIs

| Method | Route | Description |
|---|---|---|
| `POST` | `/process` | Processes a message and returns the agent decision |

Request (`ProcessRequest`, PascalCase, mirroring what the Orchestrator sends): `TenantId`, `ConversationId`, `MessageId`, `MessageType`, `Text?`, `State?`, `JourneyVersion?`, `LastIntent?`, `StructuredState?` (opaque dict, key `cpf`), `SessionReset?`, `SessionStartedAt?`.
Response (`ProcessResponse`, PascalCase): `Intent?`, `Confidence` (default `0.0`), `ReplyText?`, `RequiresHandoff` (default `false`), `HandoffReason?`, `State` (`Started`/`CustomerIdentified`), `StructuredState?` (`{"cpf": "..."}` once identified), `OutOfScope` (`true` when the question is not about limit/invoice, signaling the Orchestrator to reset the skill menu).

Errors: `400` when payload `TenantId` does not match the resolved `X-Tenant-Id`/claim; `403` when the signed `tenant_id` claim is absent or does not match `X-Tenant-Id` (checked before the payload); `401` without a valid/unexpired internal JWT; `422` when required fields are missing.

## Published events

| Topic | When | Payload | Is failure swallowed? |
|---|---|---|---|
| `agent.events` | Always, after each successful `/process` | `tenant_id`, `conversation_id`, `intent`, `confidence`, `requires_handoff`, `handoff_reason` | Yes — a `try/except` around publication only logs the error and never fails the request |

The payload does not contain the tax ID or customer text.

## Consumed events

None.

## Synchronous dependencies

| Destination | Protocol | Behavior when unavailable |
|---|---|---|
| OpenAI (`gpt-4o-mini` by default) | Strands SDK through `OpenAIModel` | 45-second timeout (`asyncio.wait_for`) → `requires_handoff=true`, `handoff_reason="agent_runtime_timeout"`. Any other exception → `requires_handoff=true`, `handoff_reason="agent_runtime_unavailable"`. No retry/tenacity; it degrades directly to handoff. **Called only when `MOCK_AGENT_ENABLED=false`** — this repository's `docker-compose.yml` defaults to `${MOCK_AGENT_ENABLED:-true}`, so local execution normally uses deterministic keyword-based `app/agent/mock.py` and never calls real OpenAI, following the same convention as `agent-runtime-renegotiation` |
| `tool-service-cartao-credito` (`:8410`, MCP) | streamable HTTP through `strands.tools.mcp.MCPClient`, signed request token (`token_use: tool_execution`) | If connection/tool listing fails, the agent continues without those tools and only logs a warning |

It does not call `conversation-memory-service` or `knowledge-service`, unlike `agent-runtime-renegotiation`.

## Persistence and infrastructure

No persistence of its own. Observability uses OpenTelemetry traces over OTLP to `jaeger:4317` and Prometheus metrics (`AGENT_REQUESTS`, `AGENT_HANDOFFS`, `AGENT_DURATION`).

## Business rules

1. **Deterministic tax-ID guard**: the agent never calls `consultar_limite_cartao`/`consultar_fatura_cartao` with a tax ID the customer did not literally provide in the conversation. This is enforced by a `BeforeToolCallEvent` hook rather than prompt instruction alone. Candidate tax IDs are extracted through regex while excluding matches that resemble phone numbers.
2. **Confidence threshold = 0.6** (configurable): forces `requires_handoff=true` when confidence is below the threshold, but only when `out_of_scope` is `false`; low confidence for an out-of-scope response does not become handoff.
3. Total LLM failure (timeout, missing credentials, etc.) never becomes an HTTP error — it degrades to a handoff decision.
4. Failure to connect to the MCP Tool Service does not block processing — the agent simply lacks those tools for that turn.
5. Kafka publication failure never fails the request.
6. **`out_of_scope`** is `true` when the question is not about limit/invoice, such as debt renegotiation or PIX, allowing `conversation-orchestrator` to reset and show the skill-selection menu again.
7. **`session_reset`**: when the previous session has expired (>15 min), the agent tells the customer and requests the tax ID again even if it was previously provided.

## Architecture references

- [ADR 0003 — MCP for governed tool calling](../adr/0003-mcp-governed-tool-calling.md)
- [ADR 0004 — Catch-log-continue resilience](../adr/0004-catch-log-continue-resilience.md)
- [Journey sequence diagrams](../architecture/sequence-diagrams.md)
