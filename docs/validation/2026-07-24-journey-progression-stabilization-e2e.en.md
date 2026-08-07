# Journey Progression Stabilization (`JourneyMilestone`) — E2E — 2026-07-24

End-to-end validation of OpenSpec change `stabilize-renegotiation-journey-progression`, motivated by customer tax ID `22222222222` (multiple contracts) becoming permanently stuck in the real WhatsApp flow — the agent repeatedly said "let's continue" while admitting it could not proceed "because of the current journey stage". This run supersedes critical finding #1 from `2026-07-23-renegotiation-scenario-homologation.md` (uncontrolled loop during confirmation): the root cause identified there — `JourneyStage` progression depending on the model's free-form and unreliable `Intent` — was corrected by this change.

## Summary

**The complete journey was verified end to end using real calls to `conversation-orchestrator` `POST /messages`**, rather than direct Agent Runtime `POST /process` calls as in the previous run. This time the real Orchestrator managed the entire state machine.

| Tax ID | Scenario | Result |
|---|---|---|
| `11111111111` | Single contract, happy path | ✅ `Started → CustomerIdentified → ContractSelected → EligibilityChecked → ProposalAvailable → ProposalSelected → AgreementConfirmed → DocumentAvailable` |
| `22222222222` | Multiple contracts | ✅ `Started → CustomerIdentified → ContractSelectionPending → ContractSelected → EligibilityChecked → ProposalAvailable → ProposalSelected → AgreementConfirmed → DocumentAvailable` |

Both reached `DocumentAvailable` with a real mock document link from successful `gerar_documento`. No stage required a manual restart due to a loop, unlike the critical 23/07 finding; each turn returned a decision within a few seconds.

Three additional bugs were discovered and fixed during this run:

1. **`_override_handoff_for_stage_denial` required a success in the same turn** before clearing an incorrect `requires_handoff`. This broke the exact turn where the customer accepted an offer in free text because `JourneyStage` advances only after the turn finishes. Fixed by requiring only that every failure in the turn be a stage denial.
2. **The system prompt had no instruction to call `gerar_documento`** after a successful agreement confirmation. The agent retried `confirmar_acordo` instead. Fixed with an explicit prompt rule.
3. The model sometimes called `consultar_contratos` with a truncated `client_id` such as `"1111"` or `"2222"` instead of the full tax ID, and `renegotiation-service`/`core-bancario-mock` silently accepted it and returned plausible data. Initially recorded as out of scope, this was later corrected after a real WhatsApp test demonstrated actual financial-data mismatch.

Two more correction rounds were triggered by a same-day real WhatsApp customer test:

4. **`ContractSelectionPending → ContractSelected` did not progress for a short customer reply such as `"2"`.** The agent tried debt/eligibility tools directly rather than re-querying contracts and stayed stuck. Fixed with an explicit prompt instruction to re-call `consultar_contratos` when the customer selects a contract.
5. **`core-bancario-mock` generated plausible data for malformed identifiers** such as truncated tax ID `"2222"` instead of rejecting them. Fixed by validating 11 numeric digits before resolving reserved or generic data.

## Environment and method

- Local stack through `docker compose up -d`, reusing the same stack as the 23/07 run.
- `agent-runtime-renegotiation` was rebuilt and restarted three times during this run, once per initial correction: mapping `confirmar_acordo → AgreementConfirmed`, relaxing the handoff override, and adding the `gerar_documento` prompt rule.
- **Key difference from 23/07:** calls went to the real `conversation-orchestrator` `POST /messages` endpoint on port 5268, using internally minted HS256 JWTs for the `whatsapp-bff` → `conversation-orchestrator` pair. This exercised the real persisted state machine (`JourneyStage` in `ops.conversation_state`, `JourneyMilestone` computed by Agent Runtime and applied by the Orchestrator) instead of manually simulating stage values.
- Helper script: `scratchpad/e2e_orchestrator.sh` (`send_message CONVERSATION_ID MESSAGE_ID TEXT`).
- State was inspected after every turn through `ops.conversation_state` and the latest channel reply through `ops.orchestrator_outbox`.
- Two conversations were intentionally abandoned after state contamination caused by real pre-fix bugs rather than retroactively repaired. Fresh conversations were used after each correction.

## Findings

### 1. Handoff override required success in the same turn — high severity, fixed

Before the fix, `_override_handoff_for_stage_denial` required `any_success and any_stage_denied and not any_other_failure`. In a live conversation the customer said "Aceito essa proposta" while persisted stage was still `ProposalAvailable`; the advance to `ProposalSelected` happens only after the turn completes. The agent prematurely tried `confirmar_acordo`, which was correctly denied by policy, but because nothing had succeeded in that turn the override failed to clear the agent's handoff request.

**Fix:** removed the `any_success` requirement. The condition became `any_stage_denied and not any_other_failure`. Unit tests were updated and the full suite passed 53/53. Live revalidation showed the turn no longer escalated unnecessarily and the stage correctly advanced to `ProposalSelected`.

### 2. `gerar_documento` unreachable because of missing prompt instruction — high severity, fixed

Even after `JourneyMilestone` correctly produced `AgreementConfirmed`, the agent did not know to call `gerar_documento` on the next turn. When asked for the agreement document, it retried `confirmar_acordo`, which was denied because confirmation had already happened.

**Fix:** added a `SYSTEM_PROMPT` rule: when `active_agreement_id` is already populated, do not call `confirmar_acordo` again; call `gerar_documento` using that identifier when the customer requests the document. Live validation succeeded on the first attempt and reached `journey_stage=DocumentAvailable` with a link such as `https://mock-documents.local/agreements/{id}.pdf`.

### 3. Truncated `client_id` accepted silently by the mock — medium severity, later fixed

In two of three full-flow attempts, the model called `consultar_contratos` with a truncated `client_id` such as `"1111"` or `"2222"`. The downstream accepted the identifier and returned data rather than reporting an error. Although the state machine could continue consistently around the wrong generated contract ID, the customer could be shown data unrelated to the tax ID they provided.

This was initially recorded as a follow-up but was subsequently promoted to a real correctness issue after the WhatsApp test described below.

## Result by conversation

### `e2e-fresh-4444` — `11111111111` — ✅ Fully verified

Seven turns covered identification → contract → debts + eligibility → simulation → acceptance → confirmation → document. Each stage advanced exactly as defined by the milestone table, and `active_contract_id`, `active_simulation_id`, and `active_agreement_id` were populated and preserved correctly across turns.

### `e2e-final-2222` — `22222222222` — ✅ Fully verified, original bug scenario

Eight turns. Turn 2 listed both contracts and asked which the customer wanted to handle, correctly entering `ContractSelectionPending` without prematurely querying debt, eligibility, or simulation. The remaining journey followed the single-contract shape and finished with successful agreement confirmation plus document link.

## Real customer test through WhatsApp — findings #4 and #5

After the scripted run was considered complete, the user performed a real WhatsApp test for conversation `5511942302556`, tax ID `22222222222`. The customer remained stuck after selecting the **Credit Card** contract with a short reply (`"2"`). Inspection of actual `conversation_messages` and Tool Service logs revealed two additional bugs.

### 4. Resolving `ContractSelectionPending` depended on an action the agent did not naturally take

The `_contracts_milestone` resolution path already existed and worked only if the agent re-called `consultar_contratos` in the same turn where the customer named a contract. Scripted tests had used explicit wording that naturally triggered that call. A real customer replying only `"2"` instead caused the agent to call `consultar_debitos`/`validar_elegibilidade`, which remained blocked because the persisted stage was still `ContractSelectionPending`.

**Fix:** added an explicit prompt rule instructing the agent to always call `consultar_contratos` again in the turn where the customer selects a contract, before debt/eligibility calls. The exact short-reply sequence was reproduced live and progressed to `ContractSelected` after the fix.

### 5. `core-bancario-mock` generated plausible data for a truncated tax ID

During revalidation, contract lookup sometimes used `"2222"` instead of `"22222222222"`. `core-bancario-mock` returned **200 OK with a fabricated but plausible contract** rather than an error because unrecognized identifiers fell through to generic mock-data generation.

**Fix:** `core-bancario-mock/Program.cs` now validates that the tax-ID portion of identifiers has exactly 11 numeric digits before generic generation or reserved-scenario lookup; malformed identifiers return `404`. Valid non-reserved tax IDs continue to receive generic mock data as before. Live reproduction confirmed that malformed IDs fail and the agent then uses the complete tax ID, resulting in `active_contract_id=22222222222-contract-2` and the correct scenario debts.

## Not verified in this run

- Real WhatsApp Cloud API outbound transport beyond the known local-environment limitation already documented in earlier validations.
- The remaining six reserved scenarios (`33333333333` through `99999999999`) through the real Orchestrator state machine; their simulation/data layer had already been exercised on 23/07.
- Free-text cancellation (`RequestedCancellation`). `ProposalSelectionDetector` covers acceptance, but the cancellation-detection logic mentioned in `design.md` was not implemented or tested in this change.
