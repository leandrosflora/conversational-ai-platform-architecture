# Business Domain Map

## Objective

Separate the conversational platform, business domains, and enterprise systems. The executable source is `contracts/functional/domains.yaml`.

!!! warning "Functional implementation versus data source"
    The **Collections** and **Card Services** domains are functionally represented and exercised end to end, but they use synthetic data and APIs from `core-bancario-mock`. This validates the journey design and integration controls, not compliance with real products, balances, contracts, or financial rules. In the target architecture, these domains must consume real APIs from the Banking Core and the responsible product systems.

## Domains

| Domain | Type | Responsibility | Current implementation |
|---|---|---|---|
| Conversational Platform | Generic | Channel, session, routing, opaque state, memory, and effects | Implemented |
| Customer Identity | Supporting | Identification, assurance, consent, and step-up | Partial |
| Collections | Core | Contracts, eligibility, offers, and formalization | Journey implemented with mocked data |
| Card Services | Core | Card inquiries and future card operations | Inquiry implemented with mocked data |
| Knowledge Management | Supporting | Content, search, validity, and evidence | Partial |
| Human Support | Supporting | Case, queue, assignment, resolution, and return | Request persisted; full lifecycle is a target |
| Campaigns and Activation | Supporting | Segmentation, offer, contact, and attribution | Target |
| Governance and Evidence | Generic | Audit, retention, policies, and risk | Baseline implemented |
| Performance and Analytics | Supporting | Funnels, quality, conversion, and costs | Partial |
| Banking Systems | External | Transactional source of truth and financial record | Simulated by the Core mock; real APIs are a target |

## Bounded contexts

### Conversational Platform

It must not know renegotiation- or card-specific fields. It stores `skill_id`, `journey_stage`, and `structured_state` as opaque values and provides Inbox/Outbox, ordering, and session guarantees.

### Collections

This context owns eligibility, simulation, acceptance, and formalization rules. The Agent Runtime interprets the conversation; financial rules remain deterministic in domain services and the Core.

In the current reference implementation, these rules and values are simplified and run over synthetic datasets. In production, eligibility, debt composition, offer calculation, agreement persistence, and document generation must be delegated to authorized banking systems.

### Card Services

This is a separate context from renegotiation. The current skill is read-only and must not receive transactional permissions through accidental reuse.

Current limits, invoice values, and due dates are synthetic. The target architecture must query real card-domain APIs while keeping the Tool Service as a governed access layer, never as the financial source of truth.

### Identity

This should evolve into a reusable context. A tax ID is not authentication state; it is an identifier used during a verification process.

### Banking Systems

`core-bancario-mock` temporarily represents this external domain to enable deterministic E2E testing. It must not be promoted as a production component. Replacing it with real APIs requires consideration of:

- API contracts and versioning;
- workload authentication and authorization;
- segregation by product and operation;
- persistent idempotency;
- consistency and concurrency;
- enterprise financial rules;
- regulatory audit;
- SLA, timeout, retry, and circuit breaker;
- data masking and classification;
- validation with non-production datasets before go-live.

## Main relationships

```text
Campaigns → Conversational Platform → Identity
                                  ├── Collections → Real Banking System APIs
                                  ├── Cards → Real card-domain APIs
                                  ├── Knowledge
                                  ├── Human Support
                                  └── Governance → Analytics
```

In the reference environment, both banking-system relationships terminate at `core-bancario-mock`.

## Dependency principles

- core domains do not depend on channel implementation;
- agents are not the source of financial truth;
- data produced by the mock must never be presented as real banking data;
- the platform does not interpret internal skill state;
- governance receives evidence but does not decide financial rules;
- analytics consumes business events instead of querying operational databases directly;
- replacing the mock with real APIs must preserve functional contracts and strengthen non-functional controls.
