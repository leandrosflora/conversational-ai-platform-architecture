# Functional Capability Map

## Objective

Organize the platform around business value, independently of the agents, services, or technologies used in the implementation.

The executable source for this map is `contracts/functional/capabilities.yaml`.

## L1 map

| Capability | Expected outcome | Current state |
|---|---|---|
| Engagement and channels | 24x7 support and channel continuity | Implemented for WhatsApp; omnichannel is a target |
| Customer identity and context | Secure access to information and operations | Identification implemented; assurance and consent are partial |
| Conversation and journey management | Consistent routing, session, and progression | Implemented |
| Collections and renegotiation | Inquiry, simulation, acceptance, and formalization | Implemented in the reference environment |
| Card servicing | Limit, invoice, and due-date inquiries | Implemented as a read-only skill |
| Enterprise knowledge | Answers grounded in approved content | Search implemented; editorial governance is partial |
| Human support | Continuity for exceptions | Request persisted; routing and resolution are target capabilities |
| Campaigns and activation | Traceable offers and conversion attribution | Target architecture |
| Governance and compliance | Audit, privacy, and AI risk | Baseline implemented |
| Performance and value management | Conversion, quality, containment, and cost | Partial technical metrics; functional funnel is a target |

## Relationship between strategy and implementation

```text
Business objective
        ↓
Functional capability
        ↓
Domain
        ↓
Journey / Skill
        ↓
Service
        ↓
API, event, and data
```

## Rules

1. A capability exists even if its technical implementation changes.
2. Skills implement capabilities; they are not capabilities by themselves.
3. Services may support several capabilities, but must have an explicit primary responsibility.
4. `target` capabilities must not be presented as available.
5. Every implemented capability must have an owner, indicator, and operational evidence.

## Next functional gaps

- assurance and step-up independent from individual skills;
- omnichannel continuity;
- agreement and payment follow-up;
- human routing and resolution;
- knowledge curation and validity management;
- campaign and attribution;
- business funnel and cost per journey.
