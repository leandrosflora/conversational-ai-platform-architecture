package platform.authz

import future.keywords.in

default allow := false

allowed_pairs := {
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

pair_allowed {
  input.audience in allowed_pairs[input.claims.sub]
}

tenant_matches {
  input.claims.tenant_id == input.tenant_id
}

financial_action {
  input.action in {"simular_proposta", "confirmar_acordo"}
}

simulation_evidence_valid {
  input.action == "simular_proposta"
  is_string(input.context.policy_id)
  input.context.policy_id != ""
}

confirmation_evidence_valid {
  input.action == "confirmar_acordo"
  is_string(input.context.policy_id)
  input.context.policy_id != ""
  is_string(input.context.message_id)
  input.context.message_id != ""
  input.context.confirmation_message_id == input.context.message_id
}

financial_evidence_valid {
  simulation_evidence_valid
}

financial_evidence_valid {
  confirmation_evidence_valid
}

allow {
  pair_allowed
  tenant_matches
  not financial_action
}

allow {
  pair_allowed
  tenant_matches
  financial_action
  financial_evidence_valid
}
