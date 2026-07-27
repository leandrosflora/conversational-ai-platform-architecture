package platform.authz

import future.keywords.in

test_read_allowed {
  allow with input as {
    "claims": {"sub": "renegotiation-service", "tenant_id": "00000000-0000-0000-0000-000000000001"},
    "audience": "core-bancario-mock",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "action": "consultar_cliente",
    "resource": "/clients/11111111111",
    "context": {},
  }
}

test_unknown_pair_denied {
  not allow with input as {
    "claims": {"sub": "knowledge-service", "tenant_id": "00000000-0000-0000-0000-000000000001"},
    "audience": "core-bancario-mock",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "action": "consultar_cliente",
    "resource": "/clients/11111111111",
    "context": {},
  }
}

test_unknown_action_denied {
  not allow with input as {
    "claims": {"sub": "renegotiation-service", "tenant_id": "00000000-0000-0000-0000-000000000001"},
    "audience": "core-bancario-mock",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "action": "confirmar_acord",
    "resource": "/simulations/sim-1/confirmations",
    "context": {
      "policy_id": "policy-1",
      "message_id": "message-1",
      "confirmation_message_id": "message-1",
    },
  }
}

test_tenant_mismatch_denied {
  not allow with input as {
    "claims": {"sub": "renegotiation-service", "tenant_id": "00000000-0000-0000-0000-000000000001"},
    "audience": "core-bancario-mock",
    "tenant_id": "00000000-0000-0000-0000-000000000002",
    "action": "consultar_cliente",
    "resource": "/clients/11111111111",
    "context": {},
  }
}

test_confirmation_without_evidence_denied {
  not allow with input as {
    "claims": {"sub": "renegotiation-service", "tenant_id": "00000000-0000-0000-0000-000000000001"},
    "audience": "core-bancario-mock",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "action": "confirmar_acordo",
    "resource": "/simulations/sim-1/confirmations",
    "context": {},
  }
}

test_confirmation_with_bound_evidence_allowed {
  allow with input as {
    "claims": {"sub": "renegotiation-service", "tenant_id": "00000000-0000-0000-0000-000000000001"},
    "audience": "core-bancario-mock",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "action": "confirmar_acordo",
    "resource": "/simulations/sim-1/confirmations",
    "context": {
      "policy_id": "policy-1",
      "message_id": "message-1",
      "confirmation_message_id": "message-1",
    },
  }
}
