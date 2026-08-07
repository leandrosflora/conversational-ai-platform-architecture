# whatsapp-bff

Repo: [`leandrosflora/whatsapp-bff`](https://github.com/leandrosflora/whatsapp-bff) · Stack: .NET 8, Minimal API, Confluent.Kafka · Local port: `5153`

## Primary responsibility

Channel BFF between the WhatsApp Cloud API and `conversation-orchestrator`. It receives and validates WhatsApp webhooks, persists the raw delivery to Kafka before acknowledging receipt (ensuring that a process crash does not lose already accepted messages), forwards messages asynchronously to the Orchestrator with retry-until-success behavior, and exposes an internal endpoint to send responses back to the customer through the Graph API.

Main functions:
- Verify the webhook configured in Meta (`GET /webhooks/whatsapp`).
- Validate the HMAC-SHA256 signature (`X-Hub-Signature-256`) of every delivery.
- Deduplicate repeated deliveries by `message.id`.
- Publish the raw payload to Kafka before acknowledging receipt to Meta.
- Consume that same topic and forward messages to the Orchestrator.
- Publish canonical received-message/status events.
- Send outbound messages through the WhatsApp Cloud API.

## Data owned by the service

Domain models (`Domain/`): `InboundChannelMessage`, `MessageStatusEvent` (+ `StatusError`), `OutboundChannelMessage`, `InteractiveReply`, `ChannelMessageType` (enum `Text=0, Interactive=1, Unsupported=2` — fixed order for serialization compatibility with `conversation-orchestrator`), `MessageDeliveryStatus`. None of these models is persisted in a database; they exist only while processing an HTTP request or Kafka message. There is, however, one real persisted state: an outbound idempotency reservation in Redis (`IOutboundDeliveryStore`, keyed by `tenantId` + `Idempotency-Key`), used by `POST /internal/messages`.

## Published APIs

| Method | Route | Description |
|---|---|---|
| `GET` | `/webhooks/whatsapp` | Webhook verification handshake (`hub.mode`, `hub.verify_token`, `hub.challenge`) |
| `POST` | `/webhooks/whatsapp` | Receives WhatsApp Cloud API deliveries (messages and status events) |
| `POST` | `/internal/messages` | Internal endpoint (JWT + `X-Tenant-Id`) used by the Orchestrator to send a response to the customer |

`POST /webhooks/whatsapp` returns `200 OK` (accepted or duplicate discarded), `400 Bad Request` (invalid payload), `401 Unauthorized` (missing/invalid signature), or `503 Service Unavailable` (Kafka persistence failure, signaling Meta to redeliver).

`POST /internal/messages` requires `Authorization: Bearer <JWT>` (`401` if missing/invalid), `X-Tenant-Id` matching the signed `tenant_id` claim (`403` otherwise), and an `Idempotency-Key` header (`400` if missing). With a new idempotency key, it performs the send; if the key was completed previously, it returns `202 Accepted` with `{"messageId", "duplicate": true}` without sending again; if the key is associated with an in-progress or ambiguous send, it returns `409 Conflict` (`reconciliationRequired: true`). Other responses: `400 Bad Request` when `to`/`text` is missing or `buttons` is absent/empty/has more than 3 items for `type=interactive`, and `502 Bad Gateway` for an ambiguous WhatsApp Cloud API failure — the Redis reservation is **not** released in that case, preventing an automatic duplicate resend and requiring manual reconciliation.

## Published events

| Topic | When | Payload | Is failure swallowed? |
|---|---|---|---|
| `channel.webhook.received` | Always, before responding to the webhook (synchronously inside the request) | Raw delivery JSON; key = sender phone number; `CorrelationId` header | **No** — failure intentionally becomes `503` |
| `channel.message.received` | After forwarding to the Orchestrator succeeds | `InboundChannelMessage` | Yes (catch-log-continue) |
| `channel.message.status` | For every WhatsApp status event received | `MessageStatusEvent` (with `IsKnownMessage`) | Yes (catch-log-continue) |
| `channel.webhook.received.retry` | When delivery processing fails (invalid JSON, `Orchestrator` rejected it, exception) and `MaxDeliveryAttempts` has not yet been exhausted (default 5) | Same raw payload with incremented `x-delivery-attempt` and `retry-reason` headers | If the retry publish itself fails, the consumer performs `Seek` back to the original offset rather than losing the delivery |
| `channel.webhook.received.dlq` | When the delivery is poison (invalid JSON/null payload) or retry attempts are exhausted | Raw payload + `x-delivery-attempt`, `dead-letter-reason`, and original topic/partition/offset | Same replay-on-publish-failure behavior as above |

## Consumed events

`channel.webhook.received` **and** `channel.webhook.received.retry` — both consumed by the same process through `KafkaWebhookConsumerService` using the same consumer group, not by another service.

## Synchronous dependencies

| Destination | Call | Behavior when unavailable |
|---|---|---|
| `conversation-orchestrator` (`:8000` local dev / `:5268` through `docker compose`) | `POST /messages` | `AddStandardResilienceHandler`: up to 2 additional attempts, `AttemptTimeout=30s`, `TotalRequestTimeout=35s`. If the entire delivery fails (all HTTP attempts exhausted or the Orchestrator rejects it), the consumer republishes to `channel.webhook.received.retry` with a fixed `RetryBackoffSeconds` backoff (default 2s) up to `MaxDeliveryAttempts` (default 5), then sends it to the DLQ. It never performs infinite `Seek`/replay on the same offset except as a fallback if the retry/DLQ publish itself fails |
| WhatsApp Cloud API (Graph API) | `POST /{phone-number-id}/messages` | Failure becomes `502 Bad Gateway` on `POST /internal/messages` — this is **always** the case in local/demo environments without a real WhatsApp Business Account configured, not only when the Graph API is unavailable |

> The 2026-07-13 validation ([report](../validation/2026-07-13-e2e-journey.md)) observed the same inbound message being processed twice by the Agent Runtime when the Orchestrator exceeded the then-current 10-second timeout — the Orchestrator did not deduplicate by `MessageId`. The Orchestrator now maintains a transactional Inbox in PostgreSQL keyed by `(tenant_id, message_id)` (`ops.message_inbox`; see [conversation-orchestrator](conversation-orchestrator.md)), which resolves that scenario: a second delivery of the same `messageId` finds the row already `completed` or still under a valid `processing` lease and does not reprocess it. The `whatsapp-bff` timeout was also increased to `AttemptTimeout=30s`/`TotalRequestTimeout=35s`.

## Persistence and infrastructure

- **Kafka**: durable ingress queue (`channel.webhook.received` + `.retry` + `.dlq`) and canonical outbound events.
- **Redis**: idempotency reservation for `POST /internal/messages` (`IOutboundDeliveryStore`), keyed by tenant + `Idempotency-Key`.
- **Webhook delivery deduplication**: in memory (`IMessageDedupeStore`), lost on restart.
- **Known outbound-message tracking**: in memory, also lost on restart.
- No relational or document database.

## Business rules

1. The webhook is acknowledged to Meta with `200 OK` only after the raw payload has been durably published to Kafka — never before.
2. The Kafka consumer advances and commits the offset only after the delivery is successfully processed **or** the corresponding retry/DLQ message is successfully published; if neither processing nor retry/DLQ publishing succeeds, the consumer performs `Seek` back to the original offset rather than losing the delivery.
3. A poison delivery (invalid JSON or null payload) goes directly to the DLQ without retry — reprocessing the same bytes could never succeed.
4. A delivery that fails for another reason (Orchestrator rejection, processing exception) is republished to `channel.webhook.received.retry` with fixed backoff until `MaxDeliveryAttempts` (default 5) is exhausted, and only then moves to the DLQ.
5. Webhook deduplication: a delivery is considered duplicate only if **all** `message.id` values in it were already processed.
6. `POST /internal/messages` is idempotent by `Idempotency-Key`: a completed key returns the same `messageId` without resending; an in-progress/ambiguous key returns `409` rather than risking a duplicate send.
7. Immediately after persisting the delivery to Kafka, the service makes a best-effort, non-throwing attempt to show the customer a "typing..." indicator through `POST /{phone-number-id}/messages` (`mark_as_read` + `typing_indicator`), even before the Orchestrator/Agent Runtime responds.

## Architecture references

- [ADR 0001 — Kafka as a durable webhook ingress queue](../adr/0001-kafka-durable-webhook-queue.md)
- [ADR 0004 — Catch-log-continue resilience](../adr/0004-catch-log-continue-resilience.md)
- [Journey sequence diagrams](../architecture/sequence-diagrams.md)
