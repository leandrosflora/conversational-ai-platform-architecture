# Retention, Classification, and LGPD

## Principles

- collect only what is necessary for the journey purpose;
- separate operational identifiers from sensitive content;
- define retention by data class;
- support discovery, correction, anonymization, and deletion;
- preserve regulatory evidence without retaining content longer than necessary;
- record who executed each administrative operation.

## Initial matrix

| Class | Example | Store | Reference retention | Treatment |
|---|---|---|---:|---|
| Conversation content | text sent by the customer | MongoDB | 90 days | deletion/anonymization by data subject and tenant |
| Operational state | Inbox, state, Outbox | PostgreSQL | 180 days | purge after completion and reconciliation window |
| Audit | tool, decision, status | PostgreSQL | 5 years, subject to regulatory policy | minimize payload and restrict access |
| Session/cache | temporary context | Redis | TTL of hours/days | automatic expiration |
| Logs | technical events without content | Loki | 30 days | redaction and expiration |
| Traces | spans and correlation | Jaeger/backend | 7–14 days | no sensitive payload |
| RAG knowledge base | documents/chunks | OpenSearch/source | contractual validity | deletion at source and reindexing |

These periods are technical references, not legal decisions. Legal, Privacy/LGPD, and business teams must approve the final policy.

## Required controls

1. field catalog with classification;
2. centralized redaction before logs, metrics, and traces;
3. API/process to search by data subject and tenant;
4. deletion with tombstone and evidence;
5. anonymization when regulatory retention prevents complete deletion;
6. OpenSearch reindexing after deletion at source;
7. request-backlog metrics;
8. automated tests proving that tax IDs and content never become labels.

## Minimum evidence

Each request must record:

- request identifier;
- legal basis/purpose;
- tenant;
- stores queried;
- number of records changed;
- result and failures;
- operator/workload;
- timestamp;
- execution-report hash.
