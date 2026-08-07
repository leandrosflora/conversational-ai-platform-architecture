# Workload Identity, JWKS, and PDP

## State

The default POC profile continues to use HS256 with an independent secret for each service pair. `docker-compose.security.yml` adds an executable, isolated implementation of the target evolution:

- RS256 token issuer;
- OIDC discovery;
- JWKS publication;
- short-lived tokens per workload and audience;
- distinct bootstrap authentication per workload before issuance;
- issuer/destination pair allowlist;
- centralized OPA decisioning;
- policy requiring evidence for financial actions;
- fail-closed readiness when OPA or bootstrap credentials are invalid.

This profile demonstrates the migration and contracts. It does not replace an enterprise identity provider.

## Execution

```bash
docker compose -f docker-compose.security.yml up -d --build --wait
python scripts/validate-security-control-plane.py
docker compose -f docker-compose.security.yml down -v
```

Local endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /.well-known/openid-configuration` | OIDC discovery |
| `GET /jwks.json` | RS256 public key |
| `POST /token` | short-lived token for an allowed pair after bootstrap authentication |
| `POST /authorize` | validates JWT/tenant and queries OPA |
| `GET /health/ready` | readiness including OPA and bootstrap configuration |

## Authenticated issuance

The requester sends its identity in the body and proves possession of the corresponding bootstrap credential:

```http
POST /token
X-Workload-Bootstrap-Token: <workload credential>
Content-Type: application/json

{
  "client_id": "renegotiation-service",
  "audience": "core-bancario-mock",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "ttl_seconds": 120
}
```

The control plane:

1. resolves the expected credential for `client_id`;
2. compares it in constant time;
3. verifies that the caller/audience pair is allowed;
4. issues an RS256 token with `kid`, `sub`, `aud`, `tenant_id`, `jti`, and a short expiration.

Credentials present in Compose are local placeholders only and are distinct per workload. Production must inject them through a secret manager or eliminate shared bootstrap credentials by using native identity, SPIFFE/SPIRE, or mTLS.

## Centralized policy

`security/opa/platform.rego` receives:

```json
{
  "claims": {
    "sub": "renegotiation-service",
    "tenant_id": "00000000-0000-0000-0000-000000000001"
  },
  "audience": "core-bancario-mock",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "action": "confirmar_acordo",
  "resource": "/simulations/sim-1/confirmations",
  "context": {
    "policy_id": "policy-1",
    "message_id": "message-1",
    "confirmation_message_id": "message-1"
  }
}
```

The decision allows reads for authorized pairs, but requires `policy_id` for simulations and evidence tied to the current message for confirmations.

## Recommended migration

```text
HS256 per pair
   ↓
dual HS256 + RS256 validation
   ↓
RS256/JWKS as default
   ↓
credential issued by native workload identity
   ↓
mTLS/SPIFFE and enterprise policy
```

During dual mode, the service should record which mechanism validated each call without storing tokens or sensitive content.

## Required production controls

The local implementation authenticates issuance using per-workload bootstrap credentials. This removes self-assertion of `client_id`, but still does not equal native workload identity.

Production still requires:

- strong workload identity without shared secrets;
- keys in HSM/KMS;
- rotation and revocation;
- stable HTTPS issuer;
- high availability;
- decision logs with PII protection;
- signed OPA bundles;
- fail-closed fallback policy;
- rate limiting and auditing on the token endpoint;
- integration with IAM/OAuth2, SPIFFE/SPIRE, or native platform identity.

## Tests

`security/opa/platform_test.rego` covers allowed pairs, unknown pairs, tenant mismatch, and financial evidence. The `Security control plane` workflow starts the environment and validates:

- fail-closed readiness;
- discovery and JWKS;
- issuance denied without credentials;
- issuance denied with incorrect credentials;
- authenticated RS256 issuance;
- pair allowlist;
- positive and negative OPA decisions;
- tenant mismatch.
