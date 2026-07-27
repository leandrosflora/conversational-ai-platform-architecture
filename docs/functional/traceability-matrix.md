# Matriz de rastreabilidade funcional

## Objetivo

Mostrar como capacidades, domínios, skills, serviços, eventos e indicadores se conectam.

| Capacidade | Domínio | Skill | Serviços principais | Eventos | KPIs |
|---|---|---|---|---|---|
| Identificação do cliente | Identidade | Ambas | Agent Runtimes, Orchestrator | CustomerIdentified | contenção, conversão |
| Gestão da jornada | Plataforma | Ambas | Orchestrator | SkillOutOfScope, JourneyAbandoned | fora de escopo |
| Consulta de carteira | Recuperação | Renegotiation | Tool, Renegotiation Service, Core | DebtPortfolioPresented, ContractSelected | conclusão |
| Elegibilidade | Recuperação | Renegotiation | Renegotiation Service, Core | EligibilityAssessed | conversão |
| Simulação | Recuperação | Renegotiation | Tool, Domain, Core | OfferSimulated, OfferPresented | aceite |
| Formalização | Recuperação | Renegotiation | Tool, Domain, Core | OfferAccepted, AgreementFormalized | conversão, valor |
| Documento | Recuperação | Renegotiation | Agent, Tool | DocumentDelivered | conclusão |
| Consulta de cartão | Cartão | Card Servicing | Agent, Tool, Core | CardInformationDelivered | sucesso |
| Handoff | Atendimento Humano | Ambas | Orchestrator, Handoff | HandoffRequested/Resolved | handoff, SLA |
| Conhecimento | Knowledge | Renegotiation | Knowledge Service | evidência de busca/auditoria | groundedness |
| Auditoria | Governança | Ambas | Audit Service | todos os eventos relevantes | conformidade |

## Uso

A matriz deve ser atualizada quando:

- uma skill é adicionada;
- uma capacidade muda de `target` para `implemented`;
- um novo evento funcional entra no funil;
- ownership de domínio ou KPI muda;
- um serviço assume ou perde responsabilidade funcional.
