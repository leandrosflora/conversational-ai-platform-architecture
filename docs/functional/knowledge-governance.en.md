# Functional Knowledge Governance

## Current state

The Knowledge Service ingests PDFs by tenant, generates chunks and embeddings, and creates vector indexes. Hash and source-file metadata exist, but the full editorial lifecycle is still missing.

## Target required metadata

```yaml
knowledgeAsset:
  id: policy-renegotiation-2026
  version: 3.1
  title: Renegotiation policy
  domain: debt-recovery
  owner: Debt Recovery
  approvedBy:
    - Legal
    - Compliance
  effectiveFrom: 2026-07-01
  expiresAt: 2027-06-30
  status: published
  allowedSkills:
    - renegotiation
  allowedAudiences:
    - customer
    - human-agent
  classification: approved-for-customer
  sourceSystem: corporate-knowledge
```

## Lifecycle

```text
Draft → Review → Approved → Published → Superseded / Expired / Withdrawn
```

## Rules

1. Only `Published` and currently valid content may be used to answer customers.
2. ACL must be enforced by document and skill.
3. Every RAG response must record the `assetId`, version, and chunks used.
4. Expired content is removed from search before physical deletion.
5. Policy changes require traceable reindexing.
6. A result without sufficient evidence must trigger fallback rather than an invented answer.
7. Tenant data must not fall back to another tenant's content in production.

## Indicators

- coverage of approved content;
- groundedness;
- no-result search rate;
- expired assets still indexed;
- time from approval to publication;
- responses challenged by the owner.
