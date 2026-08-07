# Business Events Catalog

## Objective

Represent functional outcomes rather than only technical telemetry. The executable catalog is in `contracts/functional/business-events.yaml`.

## Minimum envelope

Every functional event must contain:

- `eventId`;
- `eventType`;
- `occurredAt`;
- `tenantId`;
- `journeyId`;
- `journeyVersion`;
- `skillId`;
- `correlationId`;
- `outcome`;
- `reasonCode`.

Personal data must be tokenized; free-form customer text does not belong in the standard envelope.

## Main events

| Stage | Events |
|---|---|
| Identity | `CustomerIdentified` |
| Portfolio | `DebtPortfolioPresented`, `ContractSelected` |
| Eligibility | `EligibilityAssessed` |
| Offer | `OfferSimulated`, `OfferPresented`, `OfferAccepted` |
| Formalization | `AgreementFormalized`, `DocumentDelivered` |
| Card | `CardInformationDelivered` |
| Routing | `SkillOutOfScope` |
| Human support | `HandoffRequested`, `HandoffAssigned`, `HandoffResolved` |
| Completion | `JourneyAbandoned`, `PaymentConfirmed` |

## Technical distinction

Current events such as `intent.detected` and `conversation.state_changed` remain useful for operations. They do not replace business events because they do not prove that an offer was presented, accepted, or formalized.

## Rules

1. The producer is the domain that confirms the fact.
2. Financial events carry value and currency when applicable.
3. `reasonCode` uses a controlled vocabulary.
4. Events are immutable and idempotent by `eventId`.
5. Reprocessing must not duplicate indicators.
6. Events for target capabilities may exist in the catalog before implementation, but they must be identified in the roadmap.
