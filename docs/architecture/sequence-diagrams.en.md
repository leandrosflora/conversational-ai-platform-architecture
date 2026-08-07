# Sequence Diagrams — Implemented State

The diagrams describe the platform's coordinated change set. The target architecture remains defined in `C4/c4-container-target.puml`.

The PlantUML sources under `docs/architecture/sequence/` are canonical. For each source, CI generates and validates both an **SVG** and a **PNG** artifact. This page displays the PNGs and keeps the SVG available for zooming.

## 1. Message acceptance and governed operation

![Message acceptance and governed operation](sequence/message-acceptance-governed-operation.png){ loading=lazy }

### Artifacts

- [Open the vector SVG version](sequence/message-acceptance-governed-operation.svg)
- PlantUML source: `docs/architecture/sequence/message-acceptance-governed-operation.puml`

## 2. Outbox dispatcher

![Outbox dispatcher](sequence/outbox-dispatcher.png){ loading=lazy }

### Artifacts

- [Open the vector SVG version](sequence/outbox-dispatcher.svg)
- PlantUML source: `docs/architecture/sequence/outbox-dispatcher.puml`

## 3. Simulation and confirmation idempotency

![Simulation and confirmation idempotency](sequence/simulation-confirmation-idempotency.png){ loading=lazy }

### Artifacts

- [Open the vector SVG version](sequence/simulation-confirmation-idempotency.svg)
- PlantUML source: `docs/architecture/sequence/simulation-confirmation-idempotency.puml`

PostgreSQL persistence in the domain layer is the durable guarantee. The Core store is process-local and adds determinism and defense in depth during homologation.

## 4. Ingress retry and DLQ

![Ingress retry and DLQ](sequence/input-retry-dlq.png){ loading=lazy }

### Artifacts

- [Open the vector SVG version](sequence/input-retry-dlq.svg)
- PlantUML source: `docs/architecture/sequence/input-retry-dlq.puml`

## 5. Invoice and limit query

Read-only flow, intentionally without business idempotency.

![Invoice and limit query](sequence/card-invoice-limit-query.png){ loading=lazy }

### Artifacts

- [Open the vector SVG version](sequence/card-invoice-limit-query.svg)
- PlantUML source: `docs/architecture/sequence/card-invoice-limit-query.puml`

Differences from renegotiation:

- no intermediate domain service;
- authorization by identity rather than journey stage;
- no `Idempotency-Key`, because these are queries;
- tax ID is not published in `agent.events` or `tool.executed`.

## 6. Guarantees and limitations

| Aspect | Implemented guarantee |
|---|---|
| WhatsApp ingress | ACK after Kafka persistence |
| Inbox | completion after state and effects are written in the same transaction |
| Side effects | at-least-once Outbox + deduplication |
| Ordering | lease, optimistic versioning, late-message handling, and barrier |
| Tenant | UUID in the header and signed claim |
| Tools | allowlist/policy enforced by Tool and domain layers |
| Core | caller/tenant validated; mutations require a key |
| Simulation | durable PostgreSQL + process-local replay in the Core |
| Confirmation | signed evidence and idempotency on the final hop |
| Memory | uniqueness on `(tenantId, externalMessageId)` |
| Audit/Handoff | uniqueness on `(tenant_id, idempotency_key)` |

Limitations:

- Core idempotency is lost after restart;
- HS256 remains symmetric;
- Handoff does not transfer to a real human-service platform;
- the Alertmanager receiver is local/null;
- multi-repository E2E must be executed and recorded before promotion.
