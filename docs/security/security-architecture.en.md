# Security Architecture — Implemented State

This document describes the controls delivered by the coordinated change set across the architecture repository and its services. The target architecture remains defined in `docs/architecture/C4/c4-container-target.puml`.

## 1. Trust boundaries

| Boundary | Implemented control |
|---|---|
| WhatsApp → BFF | verify token and HMAC-SHA256 over the original request bytes |
| Service → service | short-lived HS256 JWT, with a different secret for each issuer/audience pair |
| Tenant → service | canonical UUID in the `tenant_id` claim and in `X-Tenant-Id` |
| Agent Runtime → Tool Service | `tool_execution` token and caller allowlist |
| Renegotiation Tool Service → domain | `governed_tool` token with tool/stage and `policy_id` bound to the operation |
| Renegotiation Service → Core | service JWT, tenant, and `Idempotency-Key`; Core restricts callers and deduplicates |
| Card Tool Service → Core | service JWT and tenant; Core restricts callers; read-only operations |
| Ingress → business | Kafka confirmed before ACK; transactional Inbox/state |
| Side effects | durable Outbox, at-least-once replay, and destination deduplication |
| Data | tenant-scoped keys, queries, and indexes |

## 2. Webhook

`whatsapp-bff` validates:

- `hub.verify_token` during the handshake;
- `X-Hub-Signature-256` on POST requests;
- HMAC-SHA256 calculated over the original body;
- rejection before business parsing or Kafka publication.

The webhook is public because the provider requires it. Internal endpoints require JWT, a signed tenant context, and, for mutable operations, an idempotency key.

## 3. Internal identity

Common claims:

```text
iss       = conversational-ai-platform
sub       = calling service
aud       = destination service
tenant_id = canonical UUID
iat/exp   = short lifetime
jti       = token identifier
kid       = issuing service
alg       = HS256
```

Each receiver:

1. resolves a key only for allowlisted callers;
2. validates signature, issuer, audience, algorithm, and expiration;
3. requires `kid == sub`;
4. compares `tenant_id` with `X-Tenant-Id`;
5. applies an endpoint/bounded-context-specific allowlist.

The body may repeat tenant information for compatibility, but it is not the source of authority.

### Identity limitation

Pair-specific HS256 reduces blast radius but remains symmetric. Production should migrate to workload identity/OAuth2, asymmetric JWT with JWKS/rotation, and/or mTLS/service mesh.

## 4. Tools and policy

### Renegotiation

The Agent Runtime issues `tool_execution` with:

- conversation and message;
- journey stage and version;
- confirmation evidence when applicable.

The Tool Service authorizes the operation deterministically and issues `governed_tool`. The Renegotiation Service revalidates:

- caller;
- signed tool matching the endpoint;
- permitted stage;
- `policy_id == Idempotency-Key`;
- confirmation evidence bound to the current message.

An LLM prompt or tool call does not authorize a financial operation by itself.

### Card

The card skill is read-only. The Tool Service validates that the caller is `agent-runtime-fatura-cartao`; the Core validates that the final caller is `tool-service-cartao-credito`. There is no stage-based policy or `Idempotency-Key` because limit/invoice endpoints create no financial side effect.

## 5. Banking Core Mock

In the integrated environment, the Core enables fail-closed authentication and accepts:

- `renegotiation-service` on customer, eligibility, contracting, and formalization APIs;
- `tool-service-cartao-credito` only on the Card API.

The Core exposes `/health/live`, `/health/ready`, and `/metrics`. Readiness returns `503` when authentication is enabled and a required secret is missing or invalid.

The Core does not receive the original `governed_tool` token. Journey authorization has already been revalidated by the Renegotiation Service; the final hop uses service identity, tenant, and idempotency.

## 6. Multitenancy

The tenant is a non-empty canonical UUID.

- Redis: keys are prefixed by tenant;
- MongoDB: queries and uniqueness include tenant;
- OpenSearch: the physical index includes the canonical tenant;
- PostgreSQL: Inbox, state, Outbox, idempotency, Audit, and Handoff include tenant;
- Core: the in-memory idempotency scope includes tenant, operation, and key.

## 7. Integrity and durability

### Ingress

- the BFF acknowledges the webhook only after Kafka publication;
- the consumer uses manual commits;
- retry/DLQ publication must be confirmed before the original commit;
- poison messages have a retry limit.

### State and effects

The Orchestrator completes the Inbox entry in the same transaction that updates the conversation version and records effects in the Outbox. A later failure keeps the obligation retryable.

### Idempotency

| Layer | Persistence | Guarantee |
|---|---|---|
| BFF outbound | Redis | same response for the same tenant/key |
| Memory | MongoDB | `(tenantId, externalMessageId)` |
| Audit/Handoff | PostgreSQL | `(tenant_id, idempotency_key)` |
| Renegotiation Service | PostgreSQL | durable request hash/response |
| Core mock | process memory | replay/conflict for simulation and confirmation |

The Core rejects mutable operations without `Idempotency-Key`, replays an identical request, and returns `409` for divergent payloads or concurrent execution. The process-local store does not replace the durable persistence provided by the Renegotiation Service or by a real Core.

## 8. Ordering

- one message per conversation holds an active lease;
- updates require the expected version;
- old messages are classified as `late_message`;
- effects carry `journey_version`;
- later versions wait for earlier effects.

## 9. PII and logging

Implemented:

- `tool.executed` events do not include arguments;
- metrics do not use tax IDs, content, tenant, or conversation ID as labels;
- handoff reasons are normalized;
- operational logs prioritize identifiers and traces.

Still required:

- centralized redaction;
- field catalog/classification and DLP;
- approved retention and disposal;
- LGPD flows for access, correction, anonymization, and deletion;
- managed encryption at rest.

See [Retention, classification, and LGPD](../governance/data-retention-lgpd.md).

## 10. Secrets and infrastructure

Compose fails when a pair-specific secret is not provided. Real values are not versioned.

Still required for production:

- secrets vault and rotation/revocation;
- workload identity/JWKS/mTLS;
- Kafka TLS/SASL/ACL;
- managed OpenSearch security and backup;
- NetworkPolicy/service mesh;
- WAF/rate limiting;
- signed images and digest/attestation enforcement.

## 11. Supply chain

This repository runs Trivy, publishes SARIF, and generates an SPDX SBOM artifact. The Core has CI with integration tests. Controls still need to be standardized across the other repositories, including:

- scanning the built image;
- SBOM per image;
- Cosign signatures;
- GitHub artifact attestations/provenance;
- blocking deployment without signature/attestation.

## 12. Security observability

Prometheus loads versioned rules and sends alerts to Alertmanager. The baseline covers:

- unavailable critical target;
- DLQ;
- processing/Outbox failures;
- late messages;
- authentication failures;
- policy denial.

The local receiver is a null receiver. Production requires real incident integration, ownership, escalation, and delivery testing.

## 13. Remaining critical gaps

1. **Identity:** pair-specific HS256 without rotation/JWKS/workload identity.
2. **Core:** in-memory idempotency; a real Core requires persistence and its own controls.
3. **Handoff:** no real human-support platform.
4. **Infrastructure:** local Kafka/OpenSearch/network without production controls.
5. **Supply chain:** signing/attestation and enforcement are not yet standardized across services.
6. **LGPD:** enterprise policy and implementation remain incomplete.
7. **DR:** local restore covers PostgreSQL/MongoDB; Kafka/OpenSearch remain reconstructible/replayable.
8. **Evidence:** the E2E workflow exists but depends on `MULTIREPO_READ_TOKEN` and a recorded execution before promotion.

## 14. Classification

The current state is a **hardened POC with transactional consistency, pair-specific identity, deterministic tool enforcement, authenticated Core integration in a test environment, and executable operational controls**. It is not yet banking production-ready.
