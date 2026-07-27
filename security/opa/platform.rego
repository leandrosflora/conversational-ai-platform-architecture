package platform.authz

import future.keywords.in

default allow := false

allowed_actions := {
  "whatsapp-bff": {
    "conversation-orchestrator": {"processar_mensagem"},
  },
  "conversation-orchestrator": {
    "agent-runtime-renegotiation": {"processar_agente"},
    "agent-runtime-fatura-cartao": {"processar_agente"},
    "conversation-audit-service": {"registrar_auditoria"},
    "conversation-handoff-service": {"solicitar_handoff"},
    "conversation-memory-service": {"projetar_memoria"},
    "whatsapp-bff": {"enviar_resposta"},
  },
  "agent-runtime-renegotiation": {
    "tool-service-renegotiation": {"executar_tool"},
    "knowledge-service": {"buscar_conhecimento"},
    "conversation-memory-service": {"consultar_memoria"},
  },
  "agent-runtime-fatura-cartao": {
    "tool-service-cartao-credito": {"executar_tool"},
  },
  "tool-service-renegotiation": {
    "renegotiation-service": {
      "consultar_cliente",
      "consultar_elegibilidade",
      "simular_proposta",
      "confirmar_acordo",
      "consultar_documento",
    },
  },
  "renegotiation-service": {
    "core-bancario-mock": {
      "consultar_cliente",
      "consultar_elegibilidade",
      "simular_proposta",
      "confirmar_acordo",
      "consultar_documento",
    },
  },
  "tool-service-cartao-credito": {
    "core-bancario-mock": {"consultar_limite", "consultar_fatura"},
  },
}

pair_allowed {
  allowed_actions[input.claims.sub][input.audience]
}

action_allowed {
  input.action in allowed_actions[input.claims.sub][input.audience]
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
  action_allowed
  tenant_matches
  not financial_action
}

allow {
  pair_allowed
  action_allowed
  tenant_matches
  financial_action
  financial_evidence_valid
}
