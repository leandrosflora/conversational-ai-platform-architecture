# Renegotiation Process Homologation — Scenarios by Tax ID — 2026-07-23

Real execution of the 10 scenarios defined in `docs/homologacao/massa-de-teste-clientes.md` against the real `agent-runtime-renegotiation` agent (`MOCK_AGENT_ENABLED=false`, `gpt-4o-mini`), with `core-bancario-mock` already updated with the per-tax-ID scenario table from OpenSpec change `validate-renegotiation-flow-scenarios`.

## Summary

**3 of 10 scenarios were fully verified as expected (0000, 3333, 9999). One had a confirmed divergence (6666). Six were partially verified** (1111, 2222, 4444, 5555, 7777, 8888: read/eligibility/simulation stages confirmed; confirmation/document stages could not be tested safely — see critical finding #1). The `core-bancario-mock` data layer was independently verified as fully correct through direct HTTP calls. Findings #1 and #2 below belong to `agent-runtime-renegotiation`/`tool-service-renegotiation`, not to the scenario table introduced by this change.

| # | Tax ID | Scenario | Result |
|---|---|---|---|
| 0 | `00000000000` | Customer not found | ✅ Verified |
| 1 | `11111111111` | Standard happy path | ⚠️ Partial — simulation OK; confirmation blocked by finding #1 |
| 2 | `22222222222` | Multiple contracts and debts | ⚠️ Partial — identification OK; confirmation not tested |
| 3 | `33333333333` | Ineligible due to critical delinquency | ✅ Verified |
| 4 | `44444444444` | Low-value debt / short delay | ⚠️ Partial — simulation OK; confirmation not tested |
| 5 | `55555555555` | High debt / severe delay | ⚠️ Partial — simulation OK; confirmation not tested |
| 6 | `66666666666` | No open debt | ❌ **Divergence** — finding #2 |
| 7 | `77777777777` | Simulation expires before confirmation | ⚠️ Partial — simulation OK with finding #3; expiration not tested through agent |
| 8 | `88888888888` | Document pending after confirmation | ⚠️ Partial — simulation OK; confirmation/document not tested |
| 9 | `99999999999` | Requested installments outside allowed range | ✅ Verified |

## Environment and method

- Local stack through `docker compose up -d`, 18 containers including seven application services. `core-bancario-mock` was rebuilt with the scenario table before startup.
- `MOCK_AGENT_ENABLED=false`, real `OPENAI_API_KEY`, and `OPENAI_MODEL_ID=gpt-4o-mini` from the reused environment.
- **Deviation from the original plan:** rather than sending signed webhooks through `whatsapp-bff`, `POST /process` on `agent-runtime-renegotiation` was called directly with internally minted HS256 JWTs using the same issuer/audience secrets the Orchestrator would use. This exercised the same real OpenAI → MCP Tool Service → Renegotiation Service → Core chain while skipping webhook/Kafka/Orchestrator/outbound-BFF transport, which had already been validated separately and whose final real WhatsApp delivery is a known local limitation.
- To simulate conversation continuity normally maintained by the Orchestrator, each customer message and agent response was manually written to `conversation-memory-service` between turns.
- `JourneyStage` was supplied manually per call: `SimulationParametersPending` for identification/eligibility/simulation and `ConfirmationPending` for confirmation attempts.

## Critical findings

### 1. Uncontrolled loop during confirmation — critical severity

While testing scenario 1111 confirmation (`JourneyStage=ConfirmationPending`, `ExplicitConfirmationMessageId` set, explicit confirmation text), the agent entered a loop repeatedly calling `confirmar_acordo`/`gerar_documento` — **more than 110 tool calls**, each preceded by a real OpenAI API call, without ever returning a decision. The `agent-runtime-renegotiation` container had to be restarted manually to stop it.

Root cause was structural:

- `ProcessRequest` did not carry a `simulation_id` from a previous turn.
- `conversation-memory-service` persisted only readable role/content; raw `simulation_id` was not exposed to the customer and therefore unavailable in later turns.
- `SIMULATION_STAGES` and `CONFIRMATION_STAGES` in Tool Service policy were intentionally disjoint, requiring simulation and confirmation in separate turns.
- The Strands agent loop had no configured hard iteration limit.

As a result, the confirmation turn lacked a valid `simulation_id`, and the agent kept retrying rather than stopping or handing off.

**Suggested follow-up:** enforce a hard iteration/time budget for `agent.invoke_async` and persist `simulation_id` across turns through structured state, memory facts, or an explicit process contract field.

### 2. `consultar_debitos` was never called — high severity

Across all 10 scenarios the agent never called `consultar_debitos`. It consistently followed `consultar_cliente → consultar_contratos → validar_elegibilidade → simular_proposta`, treating contract `OutstandingAmount` as the debt without retrieving actual `DebtItem` records.

Concrete consequence: scenario 6666 intentionally had an empty debt list. Expected behavior was to tell the customer there was no open debt. Instead, the agent simulated and offered a normal proposal based only on the existence of the contract.

**Suggested follow-up:** require `consultar_debitos` before simulation in the agent contract and/or make the domain/Core refuse simulation when the contract has no open debt, providing defense in depth beyond prompt instructions.

## Minor findings

### 3. `simular_proposta` called multiple times in one response — low severity

The system prompt says to call `simular_proposta` at most once per contract in a response. Scenario 7777 called it four times; scenario 9999 called it five times. In 9999 the repeated calls were more understandable because the customer requested an invalid 60-installment option, but both still exceeded the literal rule. Main effect: extra latency and model/tool cost.

### 4. Mock simulation amount does not derive from actual debt — informational, pre-existing

`core-bancario-mock` uses a fixed R$ 1,000.00 base in simulation regardless of the customer's real debt. In scenario 4444 the real debt was R$ 85.00 while the proposal represented R$ 850.00 after a 15% discount, producing logically inconsistent customer-facing wording. This predated the scenario-table change.

## Result by scenario

### 0 — `00000000000` — Customer not found — ✅ Verified
Agent reported that the tax ID could not be located and recommended human support. `RequiresHandoff=true`; only `consultar_cliente` was called. Matches expected behavior.

### 1 — `11111111111` — Standard happy path — ⚠️ Partial
Turn 1 identified the customer, checked contracts and eligibility, and simulated 12 installments of R$ 66.67, total R$ 800 with 20% discount, asking whether to formalize. Confirmation was blocked by critical finding #1.

### 2 — `22222222222` — Multiple contracts and debts — ⚠️ Partial
Agent identified both contracts, evaluated eligibility, and asked which contract to renegotiate before simulation. Matches expectation. Confirmation not tested.

### 3 — `33333333333` — Critical delinquency ineligible — ✅ Verified
Agent explained ineligibility, offered human support, and stopped after `validar_elegibilidade` without calling `simular_proposta`. Matches expectation.

### 4 — `44444444444` — Low-value debt / short delay — ⚠️ Partial
Simulation was offered normally despite the small debt, as expected. See finding #4 for simulated-value inconsistency. Confirmation not tested.

### 5 — `55555555555` — High debt / severe delay — ⚠️ Partial
Simulation was offered normally without an incorrect rejection based on high amount/delay. Confirmation not tested.

### 6 — `66666666666` — No open debt — ❌ Confirmed divergence
Expected: no debt to renegotiate. Observed: agent offered a simulation without ever querying debts. This is an agent behavior issue; direct Core calls confirmed the empty debt list was correct.

### 7 — `77777777777` — Simulation expires before confirmation — ⚠️ Partial
Simulation was presented, with excessive repeated simulation calls noted in finding #3. Expiration behavior was verified directly against the mock but not through the agent because of finding #1.

### 8 — `88888888888` — Document pending after confirmation — ⚠️ Partial
Clean simulation with one call. Pending-document behavior was verified directly against the mock but not through the agent because of finding #1.

### 9 — `99999999999` — Installments outside requested range — ✅ Verified
The customer requested 60 installments; the agent correctly explained that the request was invalid and offered valid alternatives up to 48 installments. Core business outcome matched expectation despite repeated simulation calls.

## Not verified in this run

- Agent-driven `confirmar_acordo` and `gerar_documento` for the six scenarios requiring those steps, blocked by critical finding #1. Their Core behavior was independently verified through direct calls.
- Real WhatsApp Cloud API delivery, already documented as unavailable for synthetic local recipients.
- `MOCK_AGENT_ENABLED=true`, since this homologation intentionally targeted real model reasoning.
