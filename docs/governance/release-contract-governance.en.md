# Release Governance and Executable Contracts

## Objective

The platform is composed of this architecture repository and 12 service repositories. A release is not a collection of moving branches: it is an immutable set of commits that was built, tested, and promoted together.

## Manifest and lock

`release/release-manifest.yaml` declares repositories, roles, and input references. Development references may be branches or tags. Before any build, `scripts/checkout-release.py` resolves each reference and writes `artifacts/e2e/release-lock.yaml` with the exact SHAs.

The lock is the promotable unit. Evidence that does not contain the lock does not prove a reproducible multi-repository release.

```bash
python -m pip install pyyaml
python scripts/checkout-release.py \
  release/release-manifest.yaml \
  ../workspace-release \
  --lock artifacts/e2e/release-lock.yaml
```

In GitHub Actions, the `Multi-repository E2E` workflow uses `MULTIREPO_READ_TOKEN` for read access only. The token is not stored in the lock or artifacts.

## Versioned contracts

| Contract | File | Guarantee |
|---|---|---|
| Internal HTTP | `contracts/openapi/internal-platform.yaml` | operations, authentication headers, tenant, and idempotency |
| Kafka | `contracts/asyncapi/platform-events.yaml` | nine topics and minimum event envelope |
| Authorization | `contracts/policy/authorization.yaml` | caller, audience, methods, paths, and obligations |
| Composition | `release/release-manifest.yaml` | inventory and roles of the 13 repositories |

Local validation:

```bash
python scripts/validate-executable-contracts.py
```

The validator fails when:

- a service or caller does not exist in the manifest;
- an internal operation does not declare JWT and tenant requirements;
- an idempotent mutation does not declare `Idempotency-Key`;
- AsyncAPI topics diverge from provisioned Kafka topics;
- an authorization rule references a nonexistent workload;
- the repository count changes without coordinated updates.

## Promotion process

```text
input manifest
        ↓
resolve to SHAs
        ↓
release-lock.yaml
        ↓
per-repository build and tests
        ↓
contracts + evals + E2E
        ↓
SBOM, checksums, and evidence
        ↓
promote the same lock
```

A release must not be rebuilt from `main`/`master` after homologation. Promotion must reuse the same SHAs and attested artifacts.

## Minimum criteria

A release is a candidate only when it has:

1. a lock with all 13 SHAs;
2. approved service pipelines;
3. approved executable contracts;
4. approved multi-repository E2E;
5. approved evals;
6. scan and SBOM per service;
7. applicable resilience evidence;
8. rollback to a known previous lock.

## Limitations

The manifest resolves code by SHA, but the local environment still builds images at test time. Production must promote already-attested images by digest, without rebuilding between environments.
