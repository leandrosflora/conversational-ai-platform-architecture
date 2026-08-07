# Post-P1 Hardening E2E Validation (JWT + Multitenancy) — 2026-07-18

Context: the nine application repositories received the P1 hardening change in sequence (internal HS256 JWT authentication plus tenant propagation across every hop; see `docs/runbook.md` §5–6 and `docs/security/security-architecture.md`). This validation covers a complete local rebuild from those changes and a real E2E test (signed webhook → `whatsapp-bff` → Kafka → `conversation-orchestrator` → `agent-runtime-renegotiation` using real OpenAI → `tool-service-renegotiation` → `renegotiation-service` → back to `whatsapp-bff` → WhatsApp Cloud API), answering: **does the environment start from scratch with these changes, and does the journey still work end to end?**

Short answer: not initially. The environment did not start: Docker Compose interpolation failed, two services did not compile, and a third issue blocked `whatsapp-bff` startup. After six fixes detailed below, the complete journey was confirmed with real authentication across all hops.

## Method

The stack was started through `docker compose up -d --build`, not local `dotnet run`, with `MOCK_AGENT_ENABLED=false` and a real `OPENAI_API_KEY`, therefore using real OpenAI reasoning rather than deterministic fallback. Two complete E2E tests were executed using signed HMAC webhooks against `whatsapp-bff`, with different synthetic phone numbers on each run to avoid inheriting journey state from previous runs.

## Bugs found and fixed

None were cosmetic; each blocked build/startup or caused a false-negative health result.

### 1. `.env` missing `INTERNAL_AUTH_SIGNING_KEY`

`docker-compose.override.yml` started requiring `INTERNAL_AUTH_SIGNING_KEY` through `${INTERNAL_AUTH_SIGNING_KEY:?Set INTERNAL_AUTH_SIGNING_KEY in .env}` across nine services, but nothing generated or documented the secret automatically. Compose failed during interpolation before starting any container. `.env.example` also omitted that variable and `DEFAULT_TENANT_ID`. Fixed by generating a local key with `python -c "import secrets; print(secrets.token_urlsafe(48))"`, adding it locally, and documenting both variables in `.env.example`.

### 2. `renegotiation-service/Program.cs` did not compile (`CS0266`)

```text
error CS0266: Cannot implicitly convert type 'IHttpStandardResiliencePipelineBuilder' to 'IHttpClientBuilder'
```

The local `AddCoreClient<TClient, TImplementation, TOptions>` function declared `IHttpClientBuilder` as its return type while returning a chain ending in `AddStandardResilienceHandler(...)`, whose type in `Microsoft.Extensions.Http.Resilience` 10.7.0 is `IHttpStandardResiliencePipelineBuilder`. No call site used the result. Fixed by changing the local function return type to `void`.

### 3. `conversation-orchestrator/Platform/PlatformServices.cs` did not compile (`CS1061`)

```text
error CS1061: 'IProducer<string, string>' does not contain a definition for 'GetMetadata'
```

`/health/ready` called `producer.GetMetadata(...)` on `IProducer<string,string>`, which does not expose the method. `whatsapp-bff` already solved this through a dedicated `IAdminClient`; the same pattern was applied to the Orchestrator.

### 4. `kafka-init` exited with code 2 and blocked `whatsapp-bff`

`docker-compose.override.yml` rewrote the `kafka-init` command to add `channel.webhook.received.retry`/`.dlq` and `--partitions 3`, splitting topic names and command arguments across differently indented YAML lines. YAML folded scalars preserve line breaks for more-indented lines, producing an invalid Bash script. Since `whatsapp-bff` depends on `kafka-init: condition: service_completed_successfully`, startup was silently blocked. Fixed by placing the topic list and `kafka-topics.sh` arguments on single lines, matching the working base Compose pattern.

### 5. `/health/ready` always returned `503 kafka_unavailable` in both Python services despite healthy Kafka

`agent-runtime-renegotiation` and `tool-service-renegotiation` called `producer.list_topics(1)` expecting `1` to mean timeout. The signature is `list_topics(topic=None, timeout=-1)`, so `1` became the topic argument and raised `TypeError`. Reproduced against the real Kafka environment and fixed by using `list_topics(timeout=1)`.

## Happy path after fixes

| Stage | Result |
|---|---|
| Webhook verification handshake | **Confirmed** — `200 OK` |
| Signed HMAC webhook → `whatsapp-bff` → Kafka | **Confirmed** — `200 OK` |
| `KafkaWebhookConsumerService` → Orchestrator `POST /messages` with JWT | **Confirmed** — `202 Accepted`, no `401`/`403` |
| Orchestrator → Agent Runtime with JWT and real OpenAI (~11s) | **Confirmed** — within `AttemptTimeout=45s` |
| Agent Runtime → `tool-service-renegotiation` via MCP JWT → `renegotiation-service` JWT | **Confirmed** — `consultar_cliente`/`consultar_contratos` returned `200 OK` |
| Orchestrator → `conversation-memory-service`, `conversation-audit-service` with JWT | **Confirmed** — session, history, and audit event persisted |
| Orchestrator → `whatsapp-bff` JWT → real WhatsApp Cloud API | **Reach confirmed**; Graph API rejected synthetic recipient with `#131030 Recipient phone number not in allowed list`, an expected local-test condition unrelated to internal authentication |
| Tenant propagated correctly (`00000000-0000-0000-0000-000000000001`) across all hops | **Confirmed** in Orchestrator and Agent Runtime logs |
| Inbox PostgreSQL deduplication — one Agent Runtime call per `MessageId` | **Confirmed**, mitigating the duplicate-processing finding from 2026-07-13 |
| `outcome=processed`, not a technical-timeout handoff | **Confirmed** |

### AgentRuntimeClient timeout note

During the same work, `conversation-orchestrator/Program.cs` was updated so `IAgentRuntimeClient` uses `AttemptTimeout=45s`, `TotalRequestTimeout=60s`, and `CircuitBreaker.SamplingDuration=90s` instead of framework defaults of 10s/30s/30s. This was necessary because real end-to-end calls involving multiple OpenAI round trips and MCP tool calls were observed at ~21–41 seconds. Other synchronous Orchestrator clients remain on 10s/30s defaults, appropriate for their observed sub-second to few-second latency.

## .NET test suites broken by hardening and fixed

`renegotiation-service.Tests` and `conversation-orchestrator.Tests` initially did not compile because of new required parameters and constructors. After compilation fixes, endpoint tests based on `WebApplicationFactory<Program>` failed with `401 Unauthorized` because default authorization now required JWTs.

Two solutions were used:

- `conversation-orchestrator` supports `InternalAuth:Enabled`; tests set `UseSetting("InternalAuth:Enabled", "false")` on the test host.
- `renegotiation-service` does not have that flag; a new `TestAuth.cs` helper issues a real JWT using the same key/issuer/audience expected by the service, exercising authentication rather than bypassing it.

Final results: `renegotiation-service.Tests` 35/35, `conversation-orchestrator.Tests` 73/73. Python suites were not audited in this run.

## Not verified in this run

- Python `pytest` suites for the four Python services.
- Full handoff path (`RequiresHandoff=true`) under the new authentication regime; the validated run ended with `outcome=processed`.
- JWT rotation/expiration under sustained load.
- Authenticated `/admin/reindex` behavior in `knowledge-service`.
