# ADR 0001: Use Kafka as a Durable Queue Between the WhatsApp Webhook and the Orchestrator

## Status

Accepted and implemented (retrospective — this ADR documents a decision already made during `whatsapp-bff` development, not a future proposal).

**Affected service:** [`whatsapp-bff`](../services/whatsapp-bff.md).

## Context

The first version of `whatsapp-bff` queued received webhooks in an **in-memory** `System.Threading.Channels.Channel<T>` and returned `200 OK` to Meta immediately afterward. A separate `BackgroundService` read from that queue and forwarded messages to `conversation-orchestrator`.

The problem: if the process crashed due to deployment, crash, or OOM after the `200 OK` but before the `BackgroundService` could forward the message, that message was lost. Because Meta had already received `200 OK`, it would never redeliver the webhook. In a banking debt-renegotiation platform, silently losing a customer message is unacceptable, especially given the full-traceability requirement already declared in `docs/context/business-context.md`.

## Decision

Replace the in-memory queue with a Kafka topic (`channel.webhook.received`) as the actual durability mechanism:

1. `POST /webhooks/whatsapp` publishes the raw payload to Kafka **before** returning `200 OK`. If publication fails, the endpoint returns `503` so Meta can redeliver.
2. A `KafkaWebhookConsumerService` (Kafka consumer rather than an in-memory channel reader) consumes the topic and forwards to the Orchestrator.
3. The offset is committed only when forwarding succeeds. On failure, the consumer performs `Seek` back to the same offset and retries after a short backoff (~2s). Merely avoiding a commit would not be enough because `Consume()` advances independently of commits.

## Positive consequences

- A message accepted by the webhook is no longer silently lost even if the process crashes immediately afterward.
- Orchestrator unavailability becomes visible backpressure through continuous logged retries rather than silent data loss.
- The topic also provides an audit trail of the raw received payload.

## Negative consequences

- A forwarding failure reprocesses the entire delivery. If a delivery contains several WhatsApp messages and only one fails, messages already forwarded successfully may be sent to the Orchestrator again.
- Kafka becomes a hard dependency in the webhook's critical path: if Kafka is down, `whatsapp-bff` returns `503` instead of accepting the message. The previous design always accepted messages, at the cost of the loss risk that motivated this decision.
- `KafkaWebhookConsumerService` becomes another component to operate and observe.

## Rules

- The `channel.webhook.received` offset is committed only after all messages in the delivery are successfully forwarded to the Orchestrator.
- A message that cannot be deserialized again because the payload is corrupt is treated as a *poison message*: it is logged as an error and committed rather than retried forever, because reprocessing the same bytes could never succeed.
- The original delivery `CorrelationId` is propagated as a Kafka header to enable end-to-end log correlation.
