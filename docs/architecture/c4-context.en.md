# C4 Model

## How to read the architecture

The documentation keeps two views separate so that planned architecture is never mistaken for existing implementation:

| Level | Implemented state | Target architecture |
|---|---|---|
| Context | [Open implemented view](c4-context-current.md) | [Open target view](c4-context-target.md) |
| Containers | [Open current containers](c4-container-current.md) | [Open target containers](c4-container-target.md) |

The PlantUML files under `docs/architecture/C4/` are the canonical sources. For each source, CI generates and validates both an **SVG** and a **PNG** artifact. MkDocs displays the PNGs and keeps the SVG available for zooming.

## Implemented context

[![C4 Context — Implemented State](C4/c4-context.png){ loading=lazy }](c4-context-current.md)

Represents the systems that are actually integrated and executable in the workspace.

## Target context

[![C4 Context — Target Architecture](C4/c4-context-target.png){ loading=lazy }](c4-context-target.md)

Represents the ecosystem expected for production, including enterprise systems that are not yet integrated.

## Current containers

[![C4 Container — Implemented State](C4/c4-container-current.png){ loading=lazy }](c4-container-current.md)

Details the services, datastores, queues, and observability components available today.

## Target containers

[![C4 Container — Target Architecture](C4/c4-container-target.png){ loading=lazy }](c4-container-target.md)

Details the capabilities and integrations required for enterprise production.

## Implemented state

### Actors and external systems

| Element | Current role |
|---|---|
| Customer | Interacts through WhatsApp in debt renegotiation and card inquiry journeys |
| WhatsApp Cloud API | Delivers webhooks and receives outbound messages |
| OpenAI | Provides language and embedding models when mock mode is disabled |
| Banking Core Mock | Exposes local renegotiation, limit, and invoice APIs using synthetic data |

### Platform boundary

The implemented Conversational AI Platform contains:

- a Channel BFF for webhook validation, durable ingress, and outbound responses;
- a Conversation Orchestrator with Inbox, state, and transactional Outbox;
- two agent skills: debt renegotiation and card invoice/limit inquiries;
- MCP Tool Services with authorization and operation isolation;
- a renegotiation domain service and Banking Core Mock;
- Knowledge Service, Conversation Memory, Audit Service, and Handoff Service;
- PostgreSQL, MongoDB, Redis, OpenSearch, and Kafka;
- Jaeger, Loki, Grafana Alloy, Prometheus, and Grafana.

### Current limitations

- The Handoff Service persists transfer requests but is not yet integrated with a real customer service platform.
- Salesforce, Data Lake, and campaign automation are not called by the code.
- The knowledge base consists of PDFs mounted locally in `knowledge-service`.
- The Banking Core is a mock and does not represent real financial rules or complete production controls.
- The implemented channel is WhatsApp Cloud API; other channels belong to the target view.

## Enterprise target architecture

The target view adds capabilities that must not be confused with the current state:

| Target capability | Workspace status |
|---|---|
| Salesforce and campaign segmentation | Not implemented |
| Data Lake and regulatory retention | Not implemented |
| Data product / campaign automation | Not implemented |
| Bidirectional customer service platform | Not implemented |
| Enterprise knowledge base with classification and ACL | Partial: local PDFs by tenant |
| AI Model Gateway with multiple providers | Not implemented; direct OpenAI call |
| Real Banking Core and card APIs | Not implemented; P10 defines ports and onboarding criteria |
| Workload identity, mTLS, and key rotation | Not implemented |
| Central PDP with OPA/Cedar | Not implemented |
| Managed Kafka with TLS/SASL and Schema Registry | Not implemented |
| Immutable audit and governed export | Partial: local PostgreSQL |

## Update criterion

A dependency should move from the target view to the implemented view only when there is at least one of the following pieces of evidence:

1. confirmed integration in code;
2. executable configuration in Compose or equivalent infrastructure;
3. an automated test or recorded E2E evidence under `docs/validation/`.

Intent documents, future ADRs, and isolated conceptual diagrams are not evidence of implementation.
