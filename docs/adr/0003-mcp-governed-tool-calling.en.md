# ADR 0003: Use MCP for Governed AI-Agent Tool Calling

## Status

Accepted and implemented (retrospective).

**Affected services:** [`agent-runtime-renegotiation`](../services/agent-runtime-renegotiation.md), [`tool-service-renegotiation`](../services/tool-service-renegotiation.md).

## Context

`agent-runtime-renegotiation` needs to perform actions in enterprise systems — customer lookup, offer simulation, agreement confirmation — based on LLM decisions. Giving the agent direct access to arbitrary HTTP clients would make it difficult to audit which actions were actually executed, version the available tool set, or replace the agent/model without rewriting integration with `renegotiation-service`.

## Decision

Introduce a dedicated MCP server (`tool-service-renegotiation`) as the only entry point for agent actions over the renegotiation domain. `agent-runtime-renegotiation` connects through `strands.tools.mcp.MCPClient` over streamable HTTP and lists available tools on each request. The MCP server exposes seven tools (`consultar_cliente`, `consultar_contratos`, `consultar_debitos`, `validar_elegibilidade`, `simular_proposta`, `confirmar_acordo`, `gerar_documento`), each mapped 1:1 to a `renegotiation-service` endpoint, and publishes a `tool.executed` audit event for each execution.

## Positive consequences

- Every agent action over the domain passes through one auditable point with a Kafka event per call.
- The tool set is declared and versioned in `tool-service-renegotiation`, rather than scattered through agent code.
- Sensitive arguments such as tax IDs and identifiers are never published in the audit event; only tool name and outcome are included.
- If `tool-service-renegotiation` is unavailable, the agent degrades by continuing without those tools rather than failing all message processing.

## Negative consequences

- An additional indirection layer (agent → MCP → HTTP → Banking Core mock) for every action, adding latency.
- `renegotiation-service` errors reach the agent as MCP `ToolError` values rather than structured successful responses, so the agent must handle that type of failure.

## Rules

- Every tool exposed by `tool-service-renegotiation` must correspond to exactly one `renegotiation-service` endpoint; no additional business logic belongs in the MCP layer.
- The `tool.executed` payload never includes tool arguments.
