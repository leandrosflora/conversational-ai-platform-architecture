# Generalização do orchestrator para multi-agente — E2E — 2026-07-24

Validação end-to-end da change OpenSpec `generalize-orchestrator-for-multi-agent`: `conversation-orchestrator`
deixou de ter qualquer conhecimento compilado do domínio de renegociação (enum `JourneyStage` de 17
valores, classificador de palavras-chave em português, campos nomeados `ActiveContractId`/
`ActiveSimulationId`/`ActiveAgreementId`) e passou a ser um chassi genérico: resolve qual "skill"
(agente) atende uma conversa via um novo `AgentSkillRegistry`, encaminha a mensagem, e persiste o
`State`/`StructuredState` opacos que o agente resolvido reportar — sem interpretar o significado de
nenhum dos dois. A jornada de renegociação existente foi migrada para esse modelo genérico como a
primeira (e única, nesta change) skill registrada.

## Resumo

**Jornada completa verificada end-to-end através da máquina genérica**, para os dois cenários
reservados relevantes (mesmos usados nas validações anteriores desta mesma change de estabilização
de jornada, agora rodando por cima do chassi genérico):

| CPF | Cenário | Resultado |
|---|---|---|
| `11111111111` | Contrato único | ✅ `CustomerIdentified → ContractSelected → EligibilityChecked → ProposalAvailable → ProposalSelected → AgreementConfirmed → DocumentAvailable` |
| `22222222222` | Múltiplos contratos, seleção por resposta curta ("2") | ✅ `ContractSelectionPending → ContractSelected` (resolução correta via `agent-runtime-renegotiation`, não mais via lógica no orchestrator) |

Além disso, verificado que uma conversa de um tenant **sem skill configurada** é tratada como
handoff-worthy corretamente, sem exceção não tratada — `journey_stage=HandoffRequested`,
`skill_id` permanece nulo, efeito de handoff registrado com `Reason=skill_not_configured`.

`ops.conversation_state` migrado com sucesso: colunas `active_contract_id`/`active_simulation_id`/
`active_agreement_id` removidas, `skill_id` e `structured_state` (jsonb) adicionadas, `journey_stage`
mantida (já era texto livre, sem necessidade de rename).

## Ambiente e método

- Stack local via `docker compose up -d`. `conversation-orchestrator` e `agent-runtime-renegotiation`
  reconstruídos e reiniciados **juntos** (corte coordenado e quebrado, conforme documentado em
  design.md — não são independentemente implantáveis nesta change).
- Chamadas via `POST /messages` real do `conversation-orchestrator` (porta 5268), usando o mesmo
  script `scratchpad/e2e_orchestrator.sh` das validações anteriores.
- Estado verificado a cada turno via `SELECT journey_stage, skill_id, structured_state FROM
  ops.conversation_state WHERE conversation_id=...` — confirmando não só a jornada, mas que
  `skill_id` fica fixado (`"renegotiation"`) desde o primeiro turno e que `structured_state`
  acumula corretamente as chaves `contract_id`/`simulation_id`/`agreement_id` entre turnos.
- Teste do tenant sem skill: token JWT mintado manualmente para um `tenant_id` arbitrário sem
  entrada em `TenantSkillAssignments`, enviado direto para `/messages`.

## Achados

### 1. Bug real de disposal de `JsonDocument` encontrado e corrigido durante a implementação

`IngestMessageUseCase.cs` originalmente usava `using var priorStructuredState = ...` para o
`JsonDocument` reconstruído do `StructuredState` persistido. Isso descarta o objeto assim que
`ExecuteAsync` retorna — inofensivo no fluxo real (a chamada HTTP real serializa o valor antes do
`await` completar), mas quebra qualquer teste que inspecione o `AgentRuntimeRequest` capturado por
um mock *depois* que `ExecuteAsync` já terminou (exatamente o padrão usado nos testes deste
projeto). Corrigido removendo o `using` — `JsonDocument.Dispose()` só libera buffers de pool mais
cedo, não é uma correção de corretude aqui. Descoberto pelo teste reescrito de round-trip do
`StructuredState`, não ao vivo.

### 2. Investigação de `structured_state` vazio revelou não ser um bug de wiring

Ao vivo, `e2e-generic-1111` turno 2 (`consultar_contratos` bem-sucedido, CPF de contrato único)
reportou `structured_state={}` mesmo com o `journey_stage` avançando corretamente para
`ContractSelected` — inicialmente parecia um bug real na integração C#↔Python. Isolado via um teste
FastAPI ad-hoc rodando o endpoint `/process` real com `invoke_agent` mockado: o caminho completo
(empacotamento em Python → JSON HTTP → `JsonDocument` em C# → `jsonb` no Postgres) funciona
corretamente quando o modelo *de fato* preenche `active_contract_id` na decisão estruturada — o que
foi confirmado no turno seguinte da mesma conversa, onde `structured_state` populou e permaneceu
correto pelo resto da jornada. Não é uma regressão desta change: é a mesma característica de
inconsistência do LLM já documentada nos achados de hoje mais cedo (truncamento de CPF), agora só
mais visível por `structured_state` ser um único blob JSON fácil de inspecionar por completo em vez
de três campos nomeados separados.

## Não verificado nesta rodada

- As skills de PIX, recarga de celular ou seguros — não fazem parte desta change (só o chassi
  genérico + migração da skill de renegociação já existente).
- Roteamento por identidade de canal (múltiplas skills no mesmo tenant) — explicitamente fora de
  escopo (Open Question em design.md), já que `InboundChannelMessage` não carrega essa informação
  hoje.
- Rollback real da migração de schema (`ALTER TABLE ... ADD/DROP COLUMN`) — não testado
  ativamente, apenas documentado como aceitável em design.md dado que este é um ambiente de
  demonstração/homologação sem dados de produção reais em jogo.
