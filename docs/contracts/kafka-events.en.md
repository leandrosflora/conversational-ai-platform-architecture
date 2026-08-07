# Kafka Events

**Source of truth:** source-code scan on 2026-07-06, updated on 2026-07-26 with the producers for the credit-card invoice/limit skill and fully rescanned on the same date against the current code of every repository — discovering two `whatsapp-bff` retry/DLQ topics that no previous version of this document listed (see [`services-map.md`](services-map.md)).

## How to read this document

"Producer" and "Consumer" list **only** what was found implemented in code — not what older specs/design documents describe. A topic without a listed consumer means no service in this workspace currently reads from it, not that it necessarily should have one.

## Implemented topics

| Topic | Producer | Consumer | Status |
|---|---|---|---|
| `channel.webhook.received` | whatsapp-bff (`WhatsAppWebhookEndpoints`, synchronous, before ACK) | whatsapp-bff (`KafkaWebhookConsumerService`, same consumer group) | Implemented — producer and consumer in the same service |
| `channel.webhook.received.retry` | whatsapp-bff (`KafkaWebhookConsumerService`, when delivery processing fails and `MaxDeliveryAttempts` has not been exhausted) | whatsapp-bff (same consumer, also subscribed to this topic) | Implemented — producer and consumer in the same service |
| `channel.webhook.received.dlq` | whatsapp-bff (poison delivery or exhausted retries) | None | Produced without consumer — terminal by design |
| `channel.message.received` | whatsapp-bff (after forwarding to the Orchestrator succeeds) | None | Produced without consumer |
| `channel.message.status` | whatsapp-bff | None | Produced without consumer |
| `intent.detected` | conversation-orchestrator | None | Produced without consumer |
| `conversation.state_changed` | conversation-orchestrator | None | Produced without consumer |
| `agent.events` | agent-runtime-renegotiation, agent-runtime-fatura-cartao | None | Produced without consumer |
| `tool.executed` | tool-service-renegotiation, tool-service-cartao-credito | None | Produced without consumer |

## Topics configured in consumers but without an implemented producer

None found — every existing consumer (`KafkaWebhookConsumerService`, subscribed to `channel.webhook.received` and `channel.webhook.received.retry`) has a corresponding producer on the same topic.

## General pattern

Except for `channel.webhook.received` and `channel.webhook.received.retry` (the durable ingress queue and its retry topic, consumed by the same `KafkaWebhookConsumerService` — see [ADR 0001](../adr/0001-kafka-durable-webhook-queue.md)), **no topic published in this workspace has a real consumer**. `channel.webhook.received.dlq` is produced but never consumed — it is terminal by design, not a gap. The other six topics (`channel.message.received`, `channel.message.status`, `intent.detected`, `conversation.state_changed`, `agent.events`, `tool.executed`) currently serve as a potential audit/observability trail (kafka-console-consumer, external tools), not as the integration mechanism between implemented services — actual integration happens through synchronous HTTP calls (see [`services-map.md`](services-map.md) and the pages under [`docs/services/`](../services/)).

## Swallowed vs. propagated publish failures

By default, Kafka publish failures follow "catch-log-continue" semantics and never fail the originating request — see [ADR 0004](../adr/0004-catch-log-continue-resilience.md). The **only exception** is `channel.webhook.received`: a publish failure is intentionally propagated as `503` by `whatsapp-bff` because this is the only topic on which message durability depends.

| Topic | Is publish failure swallowed? |
|---|---|
| `channel.webhook.received` | **No** — propagated as `503` |
| `channel.webhook.received.retry` | **No** — neither swallowed nor propagated as an HTTP error: if publish fails, the consumer does not commit the original offset and seeks back to retry later |
| `channel.webhook.received.dlq` | Same replay-on-failure behavior as retry above |
| `channel.message.received` | Yes |
| `channel.message.status` | Yes |
| `intent.detected` | Yes |
| `conversation.state_changed` | Yes |
| `agent.events` | Yes |
| `tool.executed` | Yes |

## Summary matrix

| Topic | Producer | Primary consumer | Classification |
|---|---|---|---|
| `channel.webhook.received` | whatsapp-bff | whatsapp-bff (internal) | Durable queue |
| `channel.webhook.received.retry` | whatsapp-bff | whatsapp-bff (internal) | Durable queue (retry) |
| `channel.webhook.received.dlq` | whatsapp-bff | — | Dead-letter |
| `channel.message.received` | whatsapp-bff | — | Audit/observability |
| `channel.message.status` | whatsapp-bff | — | Audit/observability |
| `intent.detected` | conversation-orchestrator | — | Audit/observability |
| `conversation.state_changed` | conversation-orchestrator | — | Audit/observability |
| `agent.events` | agent-runtime-renegotiation, agent-runtime-fatura-cartao | — | Audit/observability |
| `tool.executed` | tool-service-renegotiation, tool-service-cartao-credito | — | Audit/observability |

## Practical decision

If you need to react to any of these events today, you need to implement a new consumer — none exists besides `KafkaWebhookConsumerService`. This is intentional at the current stage of the project (see [`docs/runbook.md` §7](../runbook.md)), not an accidental omission.
