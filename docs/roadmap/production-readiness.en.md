# Production Readiness and Governance Roadmap

## Status

The solution is an executable reference and a hardened POC. This change set delivers operational, evidence, and security baselines; banking production still depends on the execution platform and enterprise controls.

## Baselines completed in this change set

- Core mock with caller-specific JWT/tenant enforcement in the integrated Compose environment;
- Core health, metrics, and integration tests;
- process-local idempotent replay/conflict handling in the Core;
- multi-repository E2E workflow with commits and artifacts;
- Prometheus rules and local Alertmanager;
- protected backup/restore and chaos-drill scripts;
- k6 baseline;
- SLO, DR, LGPD, and supply-chain documentation;
- architecture-repository SBOM as an artifact.

## P0 — remaining blockers

- execute and make the multi-repository E2E workflow mandatory before releases;
- provision real alert receivers, ownership, and on-call coverage;
- replace HS256 with workload identity/JWKS and/or mTLS;
- implement retention, anonymization, and deletion approved by LGPD/Legal;
- prove periodic restore in a disposable environment;
- replace process-local mock idempotency with guarantees from the real banking system.

## P1 — supply chain

- generate an SBOM per service image;
- publish images by digest;
- sign images with Cosign;
- generate provenance attestations;
- block deployment without signature/attestation;
- standardize Trivy/SAST/SCA across all 12 services;
- relate each E2E evidence record to exact images/digests.

## P2 — scale and resilience

- load testing by journey and tenant, not only readiness;
- automated chaos drills in disposable environments;
- cost and token budgets;
- Kafka consumer lag and capacity planning;
- workload isolation and NetworkPolicy;
- approved SLOs and error budgets;
- regional recovery and continuity.

## Completion criterion

An item is complete only when it has:

1. implementation;
2. automated test;
3. evidence;
4. rollback;
5. owner;
6. monitoring;
7. updated documentation.
