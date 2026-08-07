# Business Context

## Overview

Financial institutions manage large customer portfolios with overdue contracts, past-due installments, and debt renegotiation opportunities.

Traditionally, these processes depend on contact centers, human operators, and back-office activities, leading to high operating costs, limited scalability, and inconsistent customer experiences.

The Conversational AI Platform aims to provide a digital renegotiation channel powered by Generative AI, allowing customers to negotiate debts through conversational interactions while preserving security, auditability, traceability, and regulatory-compliance requirements.

Although the first version uses WhatsApp as the primary channel, the solution must be designed as channel-agnostic so it can be reused through other communication channels in the future.

!!! warning "Scope of demonstrated data"
    The executable implementation in this repository does not access real customers, contracts, debts, offers, agreements, limits, or invoices. The **collections/renegotiation** and **credit card** functional domains operate on synthetic datasets and deterministic responses from `core-bancario-mock`. E2E tests demonstrate the journey, integration, and architectural controls; they do not represent production banking processing or validate real financial rules.

!!! info "Target architecture"
    In an enterprise deployment, `core-bancario-mock` must be replaced by real, governed APIs from the banking systems responsible for customer records, contracts, debts, eligibility, simulation, formalization, documents, limits, and invoices. This replacement must preserve or strengthen workload authentication, operation-level authorization, tenant isolation, idempotency, audit trails, API contracts, observability, and outage handling.

---

## Business Problem

Current debt-renegotiation processes face several challenges:

- High dependence on human support.
- High operating costs.
- Limited support-channel availability.
- Low scalability for credit-recovery campaigns.
- Fragmented customer experience.
- Limited personalization during negotiation.
- Long time to complete agreements.

During renegotiation, customers also frequently have questions about:

- Outstanding amounts.
- Debt composition.
- Interest and fees.
- Renegotiation rules.
- Number of installments.
- Payment conditions.
- Agreement formalization.

These interactions require continuous support and create an opportunity to use AI-based autonomous agents.

---

## Business Objectives

The platform should enable the organization to:

- Automate debt-renegotiation journeys.
- Increase agreement conversion.
- Reduce operating costs.
- Improve customer experience.
- Provide 24x7 support.
- Scale credit-recovery campaigns.
- Guarantee complete interaction traceability.
- Meet regulatory and LGPD requirements.
- Support future expansion to multiple channels.

---

## Scope

### In Scope

#### Customer Identification

The platform must validate customer identity before exposing sensitive information.

Examples:

- Tax-ID confirmation.
- Date-of-birth confirmation.
- OTP validation.
- Additional questions defined by business rules.

#### Debt Inquiry

The platform must query contracts and debts eligible for renegotiation. In the reference implementation, returned data is synthetic; in the target architecture, queries must reach the real APIs responsible for the product and financial record.

#### Conversational Support

The platform must answer customer questions using an enterprise knowledge base containing:

- Product FAQs.
- Renegotiation policies.
- Operational rules.
- Contract information.
- Internal procedures.

#### Offer Simulation

The platform must generate renegotiation offers according to business rules and eligibility criteria. The current simulation uses test values and rules; production must delegate calculation, eligibility, and persistence to the real banking system or an authorized enterprise engine.

#### Credit Card Invoice and Limit Inquiry

In addition to the renegotiation journey, the platform provides a second support skill: inquiry of total/available credit limit and current invoice amount/due date after customer identification by tax ID. This is a read-only skill with no simulation, negotiation, or formalization—the customer asks and receives the information. If the customer asks something outside this scope, such as renegotiation, while inside this skill, the platform detects the deviation and can present the options menu again.

The demonstrated credit limit, available amount, invoice, and due-date values are synthetic data returned by the Card API of `core-bancario-mock`. In the target architecture, the skill must consume real card-domain APIs without turning the agent or Tool Service into the financial source of truth.

#### Negotiation

The customer may:

- Accept an offer.
- Request new simulations.
- Compare options.
- Clarify questions before contracting.

#### Formalization

The platform must formalize the agreement through integration with the bank's internal systems. Confirmation executed in the reference environment is simulated and does not create a real financial obligation.

#### Transfer to Human Support

The platform must support transfer to a human agent when:

- The customer requests it.
- The agent lacks sufficient confidence to answer.
- An operational failure occurs.
- Business-defined restrictions apply.

#### Audit and Compliance

All relevant interactions must be recorded for audit, compliance, and traceability purposes.

---

### Out of Scope

The following items are not part of the first version:

- Processing production banking data.
- Creating real agreements, contracts, or financial obligations.
- Voice support.
- Collection-strategy management.
- Credit-policy engines.
- Internal back-office operations.
- Account opening.
- Sales of new financial products.
- Integrations with other financial institutions.

---

## Personas

### Customer

An individual or legal entity that wants to review and renegotiate existing debts.

#### Goals

- Understand their financial situation.
- Review overdue contracts.
- Simulate offers.
- Formalize agreements.
- Resolve financial issues quickly and simply.

---

### Collections Manager

Responsible for credit-recovery indicators.

#### Goals

- Increase financial recovery.
- Improve conversion rates.
- Reduce operating costs.
- Scale renegotiation campaigns.

---

### Human Support Agent

Professional responsible for handling exceptions and journeys transferred by the platform.

#### Goals

- Resolve complex situations.
- Handle exceptional cases.
- Continue negotiations initiated by AI.

---

## Entry Channels

The first version uses WhatsApp as its primary channel.

However, the architecture should support future expansion to:

- Web chat.
- Mobile applications.
- Franchise systems.
- Social networks.
- Voice channels.

---

## Business Journeys

### Journey 1 — Renegotiation Campaign

1. Salesforce CRM generates a list of customers eligible for a renegotiation campaign.
2. The list is made available in the enterprise Data Lake.
3. A data product or campaign automation consumes the list.
4. The customer receives a communication by email, SMS, Instagram, Facebook, or another activation channel.
5. The communication directs the customer to the bank's official WhatsApp account.
6. The customer starts the conversation.
7. Identity is validated.
8. Eligible debts are queried through real product APIs in the target architecture; in the reference environment, they are returned by the mock.
9. Available offers are presented.
10. The customer asks questions and requests simulations.
11. An offer is selected.
12. The agreement is formalized in the real banking system; in the reference environment, confirmation is simulated.
13. The receipt is made available to the customer.

---

### Journey 2 — Proactive Offer via WhatsApp

1. The bank sends a renegotiation offer directly through WhatsApp.
2. The customer responds to the message.
3. Identity is validated.
4. Debts are presented.
5. The customer negotiates terms and simulations.
6. The agreement is accepted.
7. The contract is formalized.
8. Confirmation is sent to the customer.

In the executable reference, all financial information and confirmations in this journey are synthetic.

---

### Journey 3 — Credit Card Invoice and Limit Inquiry

1. The customer starts a WhatsApp conversation and selects, or is routed to, the credit-card skill.
2. Identity is validated using a tax ID.
3. The customer asks for the available limit and/or current invoice amount.
4. The platform queries limit and invoice data. Today, the response comes from `core-bancario-mock`; in the target architecture, it must come from real card-domain APIs.
5. If the customer asks something outside the skill's scope, such as renegotiation, the platform identifies the deviation and presents the skills menu again.

---

## Artificial Intelligence Capabilities

### Autonomous Agent

Responsible for conducting the renegotiation journey, interpreting messages, deciding next steps, and invoking authorized enterprise tools. The agent does not calculate or invent financial values and is not the product's source of truth.

### RAG (Retrieval Augmented Generation)

Used to answer questions based on trusted enterprise information.

### Knowledge Base

Contains:

- FAQs.
- Products.
- Policies.
- Procedures.
- Business rules.

### MCP (Model Context Protocol)

Allows agents to perform actions in enterprise systems through standardized, governed tools.

Examples:

- Query customer data.
- Query contracts.
- Query debts.
- Validate eligibility.
- Simulate offers.
- Confirm agreements.
- Generate documents.
- Query credit-card limits.
- Query credit-card invoices.

---

## Non-Functional Requirements

### Security

- Authentication and authorization.
- Encryption in transit and at rest.
- Secure system integrations.

### Privacy and LGPD

- Personal-data protection.
- Data minimization.
- Audit of access and operations.

### Scalability

- Horizontal scalability.
- Stateless services whenever possible.

### Availability

- High availability.
- Fault tolerance.

### Observability

- Centralized logs.
- Operational metrics.
- Distributed tracing.

### Auditability

- Complete traceability of conversations.
- Traceability of AI decisions.
- Recording of tool and integration executions.

### Performance

- Low latency for conversational interactions.
- Response times appropriate for synchronous journeys.

### Cost Governance

- Model-consumption monitoring.
- Token controls.
- FinOps for Generative AI.
