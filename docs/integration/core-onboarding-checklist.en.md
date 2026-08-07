# Real Banking API Onboarding Checklist

## Contract and ownership

- Official, versioned OpenAPI specification;
- technical owner and business owner;
- SLA, SLO, and maintenance window;
- deprecation policy;
- representative sandbox.

## Security and data

- workload identity and operation-level authorization;
- data classification;
- encryption and secrets management;
- minimization, retention, and masking;
- approved audit trail.

## Financial consistency

- persistent idempotency;
- concurrency rules;
- value reference date;
- offer expiration;
- agreement reconciliation;
- duplicate and replay handling.

## Resilience

- timeouts and consumption limits;
- retries only for retryable errors;
- circuit breaker;
- contingency and degradation;
- provider RTO and RPO.

## Certification

- consumer-driven contract tests;
- sandbox tests;
- partial-response scenarios;
- normalized errors;
- Security, LGPD, Legal, and business validation;
- evidence that the production release does not reference a mock;
- rollback by adapter and contract version.

## Go-live

The integration can only be promoted when mandatory items are recorded as evidence in the release lock and linked to the exact digest of the certified adapter.
