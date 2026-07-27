from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import time
import uuid
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Header, HTTPException
import httpx
import jwt
from pydantic import BaseModel, Field

ISSUER = os.getenv("WORKLOAD_ISSUER", "http://security-control-plane:8700")
PUBLIC_ISSUER = os.getenv("WORKLOAD_PUBLIC_ISSUER", "http://localhost:8700")
OPA_URL = os.getenv("OPA_URL", "http://opa:8181/v1/data/platform/authz/allow")
KEY_PATH = Path(os.getenv("WORKLOAD_PRIVATE_KEY_PATH", "/data/workload-private.pem"))
ALLOWED_PAIRS: dict[str, set[str]] = {
    "whatsapp-bff": {"conversation-orchestrator"},
    "conversation-orchestrator": {
        "agent-runtime-renegotiation",
        "agent-runtime-fatura-cartao",
        "conversation-audit-service",
        "conversation-handoff-service",
        "conversation-memory-service",
        "whatsapp-bff",
    },
    "agent-runtime-renegotiation": {
        "tool-service-renegotiation",
        "knowledge-service",
        "conversation-memory-service",
    },
    "agent-runtime-fatura-cartao": {"tool-service-cartao-credito"},
    "tool-service-renegotiation": {"renegotiation-service"},
    "renegotiation-service": {"core-bancario-mock"},
    "tool-service-cartao-credito": {"core-bancario-mock"},
}


def load_bootstrap_secrets() -> dict[str, str]:
    raw = os.getenv("WORKLOAD_BOOTSTRAP_SECRETS_JSON", "{}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("WORKLOAD_BOOTSTRAP_SECRETS_JSON must be valid JSON") from exc
    if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
        raise RuntimeError("WORKLOAD_BOOTSTRAP_SECRETS_JSON must map workload names to strings")
    return value


BOOTSTRAP_SECRETS = load_bootstrap_secrets()


def valid_bootstrap_secret(value: str | None) -> bool:
    return bool(value) and len(value.encode()) >= 32


def bootstrap_configuration_errors() -> list[str]:
    errors: list[str] = []
    for workload in ALLOWED_PAIRS:
        if not valid_bootstrap_secret(BOOTSTRAP_SECRETS.get(workload)):
            errors.append(f"bootstrap_secret_missing_or_short:{workload}")
    unexpected = sorted(set(BOOTSTRAP_SECRETS) - set(ALLOWED_PAIRS))
    errors.extend(f"bootstrap_secret_unknown_workload:{name}" for name in unexpected)
    return errors


def b64url_int(value: int) -> str:
    size = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(size, "big")).rstrip(b"=").decode()


def load_or_create_private_key() -> rsa.RSAPrivateKey:
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        loaded = serialization.load_pem_private_key(KEY_PATH.read_bytes(), password=None)
        if not isinstance(loaded, rsa.RSAPrivateKey):
            raise RuntimeError("workload private key is not RSA")
        return loaded
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    temporary = KEY_PATH.with_suffix(".tmp")
    temporary.write_bytes(pem)
    os.chmod(temporary, 0o600)
    temporary.replace(KEY_PATH)
    return private_key


PRIVATE_KEY = load_or_create_private_key()
PUBLIC_KEY = PRIVATE_KEY.public_key()
PUBLIC_DER = PUBLIC_KEY.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
KEY_ID = hashlib.sha256(PUBLIC_DER).hexdigest()[:16]


class TokenRequest(BaseModel):
    client_id: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    tenant_id: uuid.UUID
    ttl_seconds: int = Field(default=300, ge=30, le=900)
    claims: dict[str, Any] = Field(default_factory=dict)


class AuthorizationRequest(BaseModel):
    audience: str = Field(min_length=1)
    tenant_id: uuid.UUID
    action: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="workload-identity-and-policy-control-plane", version="1.1.0")


@app.get("/health/live", include_in_schema=False)
def live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready", include_in_schema=False)
async def ready() -> dict[str, Any]:
    configuration_errors = bootstrap_configuration_errors()
    if configuration_errors:
        raise HTTPException(status_code=503, detail={"reason": "bootstrap_configuration_invalid", "errors": configuration_errors})
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(OPA_URL.rsplit("/v1/", 1)[0] + "/health")
            response.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"opa_unavailable:{type(exc).__name__}") from exc
    return {"status": "ready", "bootstrapWorkloads": len(BOOTSTRAP_SECRETS)}


@app.get("/.well-known/openid-configuration")
def discovery() -> dict[str, Any]:
    return {
        "issuer": ISSUER,
        "jwks_uri": f"{PUBLIC_ISSUER}/jwks.json",
        "token_endpoint": f"{PUBLIC_ISSUER}/token",
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["workload"],
        "grant_types_supported": ["client_credentials"],
        "token_endpoint_auth_methods_supported": ["x-workload-bootstrap-token"],
    }


@app.get("/jwks.json")
def jwks() -> dict[str, Any]:
    numbers = PUBLIC_KEY.public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": KEY_ID,
                "n": b64url_int(numbers.n),
                "e": b64url_int(numbers.e),
            }
        ]
    }


@app.post("/token")
def token(
    payload: TokenRequest,
    x_workload_bootstrap_token: str | None = Header(default=None),
) -> dict[str, Any]:
    expected_secret = BOOTSTRAP_SECRETS.get(payload.client_id)
    if not valid_bootstrap_secret(expected_secret) or not x_workload_bootstrap_token:
        raise HTTPException(status_code=401, detail="workload_bootstrap_authentication_required")
    if not hmac.compare_digest(expected_secret, x_workload_bootstrap_token):
        raise HTTPException(status_code=401, detail="workload_bootstrap_authentication_failed")

    allowed = ALLOWED_PAIRS.get(payload.client_id, set())
    if payload.audience not in allowed:
        raise HTTPException(status_code=403, detail="workload_pair_not_allowed")
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "sub": payload.client_id,
        "aud": payload.audience,
        "iat": now,
        "nbf": now - 1,
        "exp": now + payload.ttl_seconds,
        "jti": uuid.uuid4().hex,
        "tenant_id": str(payload.tenant_id),
        "scope": "workload",
    }
    reserved = {"iss", "sub", "aud", "iat", "nbf", "exp", "jti", "tenant_id"}
    if reserved.intersection(payload.claims):
        raise HTTPException(status_code=400, detail="reserved_claim_override")
    claims.update(payload.claims)
    access_token = jwt.encode(claims, PRIVATE_KEY, algorithm="RS256", headers={"kid": KEY_ID, "typ": "JWT"})
    return {"access_token": access_token, "token_type": "Bearer", "expires_in": payload.ttl_seconds}


@app.post("/authorize")
async def authorize(
    payload: AuthorizationRequest,
    authorization: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="bearer_token_required")
    if x_tenant_id != str(payload.tenant_id):
        raise HTTPException(status_code=403, detail="tenant_header_mismatch")
    encoded = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(
            encoded,
            PUBLIC_KEY,
            algorithms=["RS256"],
            audience=payload.audience,
            issuer=ISSUER,
            options={"require": ["iss", "sub", "aud", "exp", "tenant_id", "jti"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid_workload_token") from exc
    if claims.get("tenant_id") != str(payload.tenant_id):
        raise HTTPException(status_code=403, detail="signed_tenant_mismatch")
    opa_input = {
        "input": {
            "claims": claims,
            "audience": payload.audience,
            "tenant_id": str(payload.tenant_id),
            "action": payload.action,
            "resource": payload.resource,
            "context": payload.context,
        }
    }
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.post(OPA_URL, json=opa_input)
            response.raise_for_status()
            decision = response.json()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="pdp_unavailable") from exc
    allowed = decision.get("result") is True
    if not allowed:
        raise HTTPException(status_code=403, detail="policy_denied")
    return {
        "allowed": True,
        "policy": "platform.authz.allow",
        "subject": claims["sub"],
        "audience": payload.audience,
        "tenant_id": claims["tenant_id"],
        "kid": KEY_ID,
    }
