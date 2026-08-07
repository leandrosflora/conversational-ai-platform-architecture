# Customer Identity Functional Context

## Objective

Separate identification, authentication, and authorization from each skill's business logic.

## Assurance levels

| Level | Permitted use |
|---|---|
| `anonymous` | Public FAQ and general guidance |
| `identified` | Non-sensitive context |
| `verified` | Financial-data inquiries |
| `strong_authenticated` | Formalization and higher-risk operations |

## Shared context

```yaml
identityContext:
  subjectToken: opaque-customer-token
  assuranceLevel: verified
  verifiedAt: 2026-07-27T00:00:00Z
  expiresAt: 2026-07-27T00:15:00Z
  methods:
    - cpf
    - otp
  purposes:
    - debt_renegotiation
  channelBinding: whatsapp
  evidenceId: audit-reference
```

## Rules

1. A tax ID must not be propagated as the primary identifier between services.
2. Skills receive an opaque token and assurance level.
3. Moving to a higher-risk operation may require step-up authentication.
4. Identity-context expiration must not depend only on conversation expiration.
5. Consent and purpose must be recorded separately.
6. A channel change may invalidate `channelBinding`.
7. Identity may be reused across skills only within the permitted purpose and validity period.

## Current application

- Renegotiation and card skills require `verified`.
- Agreement confirmation is cataloged as a step-up operation.
- The current tax-ID-based implementation is a baseline, not the final identity model.
