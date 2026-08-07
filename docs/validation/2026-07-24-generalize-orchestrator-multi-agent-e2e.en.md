# Generalizing the Orchestrator for Multi-Agent — E2E — 2026-07-24

End-to-end validation of OpenSpec change `generalize-orchestrator-for-multi-agent`: `conversation-orchestrator` stopped having compiled knowledge of the renegotiation domain — the 17-value `JourneyStage` enum, Portuguese keyword classifier, and named `ActiveContractId`/`ActiveSimulationId`/`ActiveAgreementId` fields — and became a generic chassis. It resolves which skill/agent serves a conversation through a new `AgentSkillRegistry`, forwards the message, and persists the opaque `State`/`StructuredState` returned by the selected agent without interpreting either. The existing renegotiation journey was migrated to this generic model as the first and only skill registered in this change.

## Summary

**The complete journey was verified end to end through the generic state machine** for both relevant reserved scenarios:

| Tax ID | Scenario | Result |
|---|---|---|
| `11111111111` | Single contract | ✅ `CustomerIdentified → ContractSelected → EligibilityChecked → ProposalAvailable → ProposalSelected → AgreementConfirmed → DocumentAvailable` |
| `22222222222` | Multiple contracts, selection through short reply (`"2"`) | ✅ `ContractSelectionPending → ContractSelected`, resolved correctly by `agent-runtime-renegotiation`, not by Orchestrator logic |

A conversation for a tenant **without a configured skill** was also verified to become handoff-worthy without an unhandled exception: `journey_stage=HandoffRequested`, `skill_id` remains null, and a handoff effect is recorded with `Reason=skill_not_configured`.

`ops.conversation_state` migrated successfully: `active_contract_id`/`active_simulation_id`/`active_agreement_id` columns were removed, `skill_id` and `structured_state` (jsonb) were added, and `journey_stage` remained because it was already free text.

## Environment and method

- Local stack through `docker compose up -d`. `conversation-orchestrator` and `agent-runtime-renegotiation` were rebuilt and restarted **together**, as a coordinated breaking cutover documented in `design.md`.
- Calls used the real Orchestrator `POST /messages` endpoint on port 5268, through the same `scratchpad/e2e_orchestrator.sh` used in prior validations.
- State was inspected after every turn with `SELECT journey_stage, skill_id, structured_state FROM ops.conversation_state WHERE conversation_id=...`, confirming that `skill_id` remains pinned to `"renegotiation"` and `structured_state` accumulates `contract_id`, `simulation_id`, and `agreement_id` across turns.
- The no-skill tenant test used a manually minted JWT for an arbitrary `tenant_id` with no `TenantSkillAssignments` entry and sent it directly to `/messages`.

## Findings

### 1. Real `JsonDocument` disposal bug found and fixed during implementation

`IngestMessageUseCase.cs` originally used `using var priorStructuredState = ...` for the reconstructed persisted `StructuredState` `JsonDocument`. That disposed the object as soon as `ExecuteAsync` returned. Real HTTP flow usually serialized the value before the awaited call completed, so it did not fail live, but tests inspecting a captured `AgentRuntimeRequest` after `ExecuteAsync` completed saw a disposed object. The `using` was removed; early `JsonDocument.Dispose()` only returns pooled buffers earlier and was not required for correctness here.

### 2. Empty `structured_state` investigation showed no wiring bug

During live turn 2 of `e2e-generic-1111`, `consultar_contratos` succeeded and `journey_stage` advanced to `ContractSelected`, but `structured_state={}`. This initially looked like a C#↔Python integration bug. An isolated FastAPI test using the real `/process` endpoint with mocked `invoke_agent` proved the full Python packaging → HTTP JSON → C# `JsonDocument` → PostgreSQL jsonb path works when the model actually fills the contract identifier. The next turn in the same real conversation populated `structured_state`, which then remained correct for the rest of the journey. The issue was therefore model-output inconsistency rather than a regression in the generic state transport.

## Not verified in this run

- PIX, mobile top-up, or insurance skills — outside this change, which covered only the generic chassis plus migration of existing renegotiation.
- Routing by channel identity when a tenant has multiple skills — explicitly out of scope because `InboundChannelMessage` did not carry that information.
- Actual rollback of the schema migration (`ALTER TABLE ... ADD/DROP COLUMN`) — documented as acceptable for the demonstration/homologation environment but not actively tested.
