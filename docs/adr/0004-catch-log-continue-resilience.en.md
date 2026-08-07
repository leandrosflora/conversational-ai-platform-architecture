# ADR 0004: Classified Failure Handling and Degradation

## Status

**Accepted — revised by ADR 0005.**

The broad `catch-log-continue` rule is not permitted for mandatory effects. Each dependency is classified according to its impact on durability, business, customer experience, and observability.

## Class A — ingress and state durability

Examples:

- publication of `channel.webhook.received`;
- Inbox acquisition;
- versioned conversation update;
- Outbox write;
- retry/DLQ publication before offset commit.

Rule:

- failures are never swallowed;
- the webhook returns `503` when ingress is not persisted;
- the Orchestrator does not return `202` without the state + Outbox transaction;
- the consumer does not commit if retry/DLQ publication is not confirmed.

## Class B — mandatory durable effects

Examples:

- response to the customer;
- session/history projection;
- audit;
- handoff request;
- intent and state events.

Rule:

- the request records the effect in the Outbox rather than depending on synchronous destination availability;
- the dispatcher executes at-least-once delivery;
- failure keeps the effect in `failed` with backoff;
- destinations must deduplicate using a tenant-scoped key;
- an unpublished earlier effect blocks later versions of the same conversation.

There is no longer any `catch-log-continue` behavior that allows a message to complete without recording the obligation.

## Class C — mutable business operations

Examples:

- simulate an offer;
- confirm an agreement.

Rule:

- automatic HTTP retry is disabled;
- `Idempotency-Key` is mandatory;
- the Tool Service generates the key after deterministic policy evaluation;
- Renegotiation Service validates signed `policy_id` against the key;
- simulation persists request hash and response;
- ambiguous outcomes fail closed and require reconciliation while the Core does not provide proven idempotency.

## Class D — critical conversational decision

Examples:

- Agent Runtime unavailable;
- model unavailable;
- low confidence.

Rule:

- convert to an explicit handoff decision;
- do not treat it as automatic success;
- measure outcome and reason using a controlled vocabulary.

## Class E — degradable enrichment context

Examples:

- reading history to enrich the prompt;
- non-transactional knowledge search.

Rule:

- may degrade to empty history or an unavailability message;
- absence of context must never authorize a financial operation;
- every degradation needs a metric and a PII-safe log.

Memory projection no longer belongs entirely to this class: delivery is now a durable Outbox effect, although history reading remains degradable.

## Class F — poison messages

Examples:

- invalid JSON;
- null Kafka payload;
- repeated failure beyond the configured limit.

Rule:

- do not retry indefinitely;
- preserve the original payload;
- send it to the DLQ with reason and origin;
- commit only after DLQ confirmation;
- reprocessing is an administrative action.

## Timeouts

- every call must have an explicit time budget;
- timeout on a mutable operation is a potentially ambiguous outcome;
- do not automatically release an idempotency key after an external call has started;
- reconciliation must precede any new attempt when the destination does not provide proven idempotency.

## Mandatory observability

Each class must expose:

- success/error counter;
- controlled-cardinality reason or exception type;
- duration;
- distributed trace;
- tenant/correlation in logs without sensitive content;
- age and count of pending effects when applicable.

## Review rules

Every new downstream must declare:

1. dependency class;
2. timeout;
3. retry policy;
4. idempotency strategy;
5. behavior for ambiguous outcomes;
6. durability mechanism;
7. required ordering;
8. metrics and alerts;
9. sensitive-data handling.

## Relationship to ADR 0005

ADR 0005 details:

- Inbox + state + Outbox transaction;
- conversation lease and versioning;
- tool policy enforcement;
- signed tenant context;
- simulation idempotency;
- fail-closed reconciliation.
