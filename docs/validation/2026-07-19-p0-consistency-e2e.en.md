# Post-Merge P0 Consistency Policy E2E Validation (Transactional Outbox + Governed Tools) — 2026-07-19

Context: since the previous validation (`2026-07-18-p1-hardening-e2e.md`), PR `agent/p0-consistency-policy` was merged into six application repositories (`conversation-orchestrator`, `agent-runtime-renegotiation`, `tool-service-renegotiation`, `renegotiation-service`, `knowledge-service`, `conversation-memory-service`, `conversational-ai-demo-arch`), introducing a transactional Outbox in the Orchestrator and a governed-tools policy based on journey stage in `tool-service-renegotiation`. This run repeats the previous question: **does the environment start cleanly and does the journey continue working end to end?**

Short answer: the environment starts cleanly through `docker compose up -d --build` with no fixes required at startup, and the journey reaches the real WhatsApp Cloud API end to end, but **two behavioral regressions and broad test-suite breakage** were found, all traceable to the same PR.

## Method

The stack was started with `MOCK_AGENT_ENABLED=false` and a real `OPENAI_API_KEY`. Two turns were sent through signed HMAC webhooks to `whatsapp-bff` using a fresh synthetic phone number (`17865551234`):

1. "Quero renegociar minha divida" — no tax ID yet.
2. "Meu CPF eh 12345678900" — known test tax ID from `postman/local-docker-compose.postman_environment.json`.

## Happy path — what worked

| Stage | Result |
|---|---|
| Webhook verification handshake | **Confirmed** — `200 OK` |
| Signed HMAC webhook → `whatsapp-bff` → Kafka → Orchestrator | **Confirmed** — `202 Accepted` in both turns |
| Orchestrator → Agent Runtime with JWT and real OpenAI | **Confirmed** — turn 1 ~6.6s, turn 2 ~4s |
| Agent Runtime → `tool-service-renegotiation` → `renegotiation-service` → `core-bancario-mock` (`consultar_cliente`) | **Confirmed** — `GET /clients/12345678900` returned `200 OK` |
| Orchestrator → `whatsapp-bff` JWT → real WhatsApp Cloud API | **Reach confirmed**; Graph API rejected the synthetic number with `#131030 Recipient phone number not in allowed list`, the same expected drift as 18/07 |
| Tenant (`00000000-0000-0000-0000-000000000001`) propagated across all hops | **Confirmed** |

## Regressions found

### 1. `consultar_contratos` denied in the same turn where `consultar_cliente` identified the customer

The policy in `tool-service-renegotiation/app/policy.py` allowed `consultar_contratos` only from `CustomerIdentified` onward, but the `journey_stage` used to authorize tool calls was signed **once at the beginning of the turn** from the Orchestrator payload and never updated during that turn. In turn 2 the conversation started at `IdentificationPending`; `consultar_cliente` was allowed and succeeded, but the following `consultar_contratos` call was denied before reaching `renegotiation-service`, because the signed stage was still `IdentificationPending`. The stage advanced only after the full turn finished.

This was a direct regression from 18/07, where both calls succeeded in the same turn.

### 2. Outbox `channel.reply` entered effectively infinite retry for a permanently undeliverable message

When WhatsApp Cloud API rejected the test recipient, `whatsapp-bff` intentionally returned `502` for the initial ambiguous failure and then `409 Conflict` with `{"retryable": false, "reconciliationRequired": true}` on subsequent attempts because the idempotency reservation remained in progress. `ChannelReplyClient.cs` ignored that body and used `EnsureSuccessStatusCode()`, treating every non-2xx as transient. `OutboxDispatcherService` then retried with exponential backoff and no attempt limit or dead-letter path.

In production, a permanently undeliverable number could therefore create a retry every five minutes indefinitely even though the downstream explicitly reported `retryable:false`.

### 3. .NET and pytest suites broken by the same PR

| Repo | Result | Observed root cause |
|---|---|---|
| `conversation-orchestrator.Tests` | **67/73** | Endpoint tests expected synchronous client calls immediately after `POST /messages`, but effects had moved to asynchronous Outbox dispatch |
| `renegotiation-service.Tests` | **29/35** | Simulation/formalization tests expected `200 OK` and received `400`/`403` after authorization/validation contract changes |
| `tool-service-renegotiation` pytest | **17/39** | Tests did not configure the new `ToolExecutionContext`/tenant contextvar and some client method signatures had changed |

The common pattern was that production contracts changed — asynchronous dispatch, signed tenant context, stage-based authorization — without corresponding test harness updates before merge.

## Not verified in this run

- Direct persistence inspection in Memory and Audit because manual calls required internal JWTs; behavior was inferred through Orchestrator Outbox logs.
- `pytest` suites for Agent Runtime, Knowledge Service, and Memory Service.
- Full handoff and JWT rotation under load.

## Update — test suites fixed on 19/07

All 34 broken tests were fixed without changing production behavior by updating fixtures/harnesses for the new contracts: `conversation-orchestrator.Tests` 73/73, `renegotiation-service.Tests` 35/35, `tool-service-renegotiation` pytest 39/39.

## Update — findings 1 and 2 fixed on 19/07

- **Finding 1:** `IdentificationPending` was added to the allowed stages for `consultar_contratos`. Because the tool still requires a `client_id` obtained only after successful `consultar_cliente`, this allows natural chaining inside one signed turn without allowing contract lookup directly from `Started`. Regression tests were added.
- **Finding 2:** `ChannelReplyClient` now inspects the response body and raises `NonRetryableDispatchException` when `whatsapp-bff` reports `retryable:false`. `OutboxDispatcherService` parks such effects instead of retrying indefinitely; as a safety limit, any effect reaching 20 failures without an explicit non-retryable signal is also parked. Metric `orchestrator_outbox_dispatch_total{outcome="dead_letter"}` exposes the condition. Parked effects retain `status='failed'` with `next_attempt_at` far in the future for manual reconciliation.

After the fixes, suites were: `conversation-orchestrator.Tests` 78/78, `renegotiation-service.Tests` 35/35, `tool-service-renegotiation` pytest 41/41.

Both fixes were then re-exercised against the real Docker environment using a fresh synthetic number (`17865559876`):

- `consultar_cliente` and `consultar_contratos` both returned `outcome=success` in the same turn and `renegotiation-service` received `GET /clients/12345678900/contracts`.
- The first `channel.reply` attempt was treated as transient; the second received `retryable:false` and was logged as parked for manual reconciliation, with no further attempts during the next 40 seconds.

## Recommendation recorded at the time

The two behavioral findings were considered blockers for realistic multi-tool turns and correct permanent-delivery-failure handling. The recommended direction was to support same-turn progression safely and make Outbox dispatch honor downstream retryability plus a finite dead-letter policy — both directions were implemented in the same 19/07 follow-up described above.
