# Functional Traceability Matrix

## Objective

Show how capabilities, domains, skills, services, events, and indicators connect.

| Capability | Domain | Skill | Main services | Events | KPIs |
|---|---|---|---|---|---|
| Customer identification | Identity | Both | Agent Runtimes, Orchestrator | CustomerIdentified | containment, conversion |
| Journey management | Platform | Both | Orchestrator | SkillOutOfScope, JourneyAbandoned | out-of-scope rate |
| Portfolio inquiry | Recovery | Renegotiation | Tool, Renegotiation Service, Core | DebtPortfolioPresented, ContractSelected | completion |
| Eligibility | Recovery | Renegotiation | Renegotiation Service, Core | EligibilityAssessed | conversion |
| Simulation | Recovery | Renegotiation | Tool, Domain, Core | OfferSimulated, OfferPresented | acceptance |
| Formalization | Recovery | Renegotiation | Tool, Domain, Core | OfferAccepted, AgreementFormalized | conversion, value |
| Document | Recovery | Renegotiation | Agent, Tool | DocumentDelivered | completion |
| Card inquiry | Card | Card Servicing | Agent, Tool, Core | CardInformationDelivered | success |
| Handoff | Human Support | Both | Orchestrator, Handoff | HandoffRequested/Resolved | handoff, SLA |
| Knowledge | Knowledge | Renegotiation | Knowledge Service | search/audit evidence | groundedness |
| Audit | Governance | Both | Audit Service | all relevant events | compliance |

## Usage

The matrix must be updated when:

- a skill is added;
- a capability moves from `target` to `implemented`;
- a new functional event enters the funnel;
- domain or KPI ownership changes;
- a service gains or loses functional responsibility.
