# Human Case Lifecycle

## Current state

The Handoff Service persists a `pending` request. There is still no real queue, assignment, acceptance, resolution, or return to automation.

## Target model

```text
Requested
   → Queued
   → Assigned
   → Accepted
   → InProgress
   → Resolved
       ├── Closed
       └── ReturnedToAutomation

Alternative exits: Rejected, Expired, Abandoned
```

## Minimum case data

- `caseId`, `tenantId`, and `journeyId`;
- source skill and stage;
- reason and reason code;
- priority, queue, and SLA;
- AI-generated summary;
- identity context and assurance level;
- minimum required transcript;
- collected data;
- executed tools;
- presented offers;
- owner and operator;
- outcome and final disposition.

## Business rules

1. The customer should not have to repeat information that has already been verified.
2. The summary does not replace the auditable history.
3. PII must follow queue-specific minimization rules.
4. Critical cases may require a specific priority and queue.
5. `ReturnedToAutomation` requires an explicit resume state.
6. Completion must publish `HandoffResolved`.
7. SLA starts at `Requested`, not at `Accepted`.

## Recommended increments

1. correct the real conversation identity, removing the seed foreign key;
2. include `skill_id`, priority, queue, and SLA;
3. add assignment, acceptance, and closure APIs;
4. publish lifecycle events;
5. integrate a customer-service platform;
6. allow safe return to the bot.
