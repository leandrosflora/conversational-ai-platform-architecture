# agent-runtime-renegotiation

Repo: [`leandrosflora/agent-runtime-renegotiation`](https://github.com/leandrosflora/agent-runtime-renegotiation) · Stack: Python, FastAPI, Strands Agents, OpenAI · Local port: `8100`

## Primary responsibility

Hosts the AI agent (Strands Agents + OpenAI) that conducts the renegotiation journey. It receives a message from the Orchestrator, retrieves recent conversation history from `conversation-memory-service`, assembles the available tools (MCP tools from `tool-service-renegotiation` plus the knowledge-base/RAG tool), invokes the model to produce a structured decision (intent, confidence, reply text, handoff requirement), publishes an audit event to Kafka, and returns the decision.

## Data owned by the service

No persisted model — `ProcessRequest`/`ProcessResponse` (Pydantic, `app/models.py`) are wire contracts, not stored domain data.

## Published APIs

| Method | Route | Description |
|---|---|---|
| `POST` | `/process` | Processes a message and returns the agent decision |

Requires `Authorization: Bearer <internal JWT>` and `X-Tenant-Id` matching the signed `tenant_id` claim.

Request (`ProcessRequest`, PascalCase — the same generic skill-agnostic contract used by `agent-runtime-fatura-cartao`, because `conversation-orchestrator` routes between both skills): `TenantId`, `ConversationId`, `MessageId`, `MessageType`, `Text?`, `State?` (formerly `JourneyStage?`; now an opaque string interpreted only by this skill), `JourneyVersion` (default `0`), `LastIntent?`, `StructuredState?` (opaque dict: `contract_id`, `simulation_id`, `agreement_id`, `offered_alternative_contract_id`), `SessionReset` (default `false`), `SessionStartedAt?`.
Response (`ProcessResponse`, PascalCase): `Intent?`, `Confidence` (default `0.0`), `ReplyText?`, `RequiresHandoff` (default `false`), `HandoffReason?`, `State?`, `StructuredState?`.

Errors: `400` if `X-Tenant-Id`, the claim, and payload `TenantId` do not match; `401` without a valid internal JWT; `422` when required fields are missing. Contrary to an older version of this document, the endpoint does **not** always return `200`: the handler has an explicit `except Exception: raise` in `app/main.py` that increments a metric and rethrows, so an unexpected failure (for example, an MCP client error outside the handled path) becomes `500`. Expected LLM failures still degrade to a handoff decision rather than an HTTP error.

## Published events

| Topic | When | Payload | Is failure swallowed? |
|---|---|---|---|
| `agent.events` | Always, at the end of each `/process` | `conversation_id`, `intent`, `confidence`, `requires_handoff`, `handoff_reason` | Yes — the code explicitly documents that it never fails the request |

## Consumed events

None.

## Synchronous dependencies

| Destination | Protocol | Behavior when unavailable |
|---|---|---|
| `conversation-memory-service` (`:8600`) | `GET /conversations/{conversationId}/messages` via httpx | Called before the agent is constructed, only on the real path (skipped when `MOCK_AGENT_ENABLED=true`). Retries through `tenacity` (default 3 attempts, 0.2s apart); after all failures, degrades to empty history — never throws and never blocks the request |
| `tool-service-renegotiation` (`:8400`, MCP) | streamable HTTP through `strands.tools.mcp.MCPClient`, with signed governance context per call (`conversation_id`, `message_id`, `journey_stage`, `journey_version`, `confirmation_message_id` when the message is an explicit confirmation) — this is the context that `tool-service-renegotiation` validates before authorizing any tool | If connection/tool listing fails, the agent continues without those tools |
| OpenAI (`gpt-4o-mini` by default) | Strands SDK through `OpenAIModel` | Missing `OPENAI_API_KEY` or model failure → generic catch → degrades to a handoff decision (`requires_handoff=true`, `handoff_reason="agent_runtime_unavailable"`) |
| Knowledge Service (`:8500`) | `GET /search?query=...` via httpx | Retries through `tenacity` (3 attempts, 0.2s apart); after all failures, returns the string `"Base de conhecimento indisponivel no momento."` to the agent instead of raising an error |

## Persistence and infrastructure

No persistence of its own. The only state is the transient result of a `/process` call; there is no local session or cache.

## Business rules

1. **Confidence threshold = 0.6** (configurable): if `decision.confidence < 0.6`, it forces `requires_handoff=true` even when the agent did not request it, using reason `"low_confidence"` unless another reason is already present.
2. A total LLM failure (missing credentials, throttling, etc.) never becomes an HTTP error — it degrades to a handoff decision with reason `"agent_runtime_unavailable"`.
3. Failure to connect to the MCP Tool Service does not block processing — the agent simply lacks those tools for that turn.
4. Knowledge Base failure becomes a textual unavailability message injected into agent context, not an error.
5. Kafka publication failure never fails the request.
6. **Recent conversation history** (up to `conversation_memory_history_limit` messages, default 10) is fetched from `conversation-memory-service` and automatically injected into the prompt — the same "always-available context" treatment previously used for `JourneyStage`/`LastIntent`, not a tool the model chooses to call. This happens only on the real path (`MOCK_AGENT_ENABLED=false`); mock mode does not fetch history because `build_mock_decision` does not use it. Long-term memory facts (`agent_memory`) are not read because this workspace has no `user_id` distinct from the `conversation_id`.

## Architecture references

- [ADR 0003 — MCP for governed tool calling](../adr/0003-mcp-governed-tool-calling.md)
- [ADR 0004 — Catch-log-continue resilience](../adr/0004-catch-log-continue-resilience.md)
- [Journey sequence diagrams](../architecture/sequence-diagrams.md)
