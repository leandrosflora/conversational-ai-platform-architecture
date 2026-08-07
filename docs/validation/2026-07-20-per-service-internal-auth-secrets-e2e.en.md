# Post-Implementation E2E Validation of `per-service-internal-auth-secrets` — 2026-07-20

Context: the `per-service-internal-auth-secrets` change replaced the single HS256 secret (`INTERNAL_AUTH_SIGNING_KEY`) shared by all services with a distinct secret per issuer/audience pair, selected through the JWT `kid` header and validated with `kid == sub`. It was implemented in parallel across the nine application repositories. This run asks the same question as previous validations: **does the environment start from scratch and does the journey still work end to end under the new secret model?**

## Method

`docker compose up -d --build` recreated all 10 application services. `.env` was rebuilt with 10 newly generated random pair-specific secrets plus the real OpenAI and WhatsApp Cloud API credentials already in use. Two turns were sent through signed HMAC webhooks to `whatsapp-bff` using a fresh synthetic phone number (`17865552468`):

1. "Quero renegociar minha divida" — no tax ID yet.
2. "Meu CPF eh 12345678900" — known test tax ID.

## Happy path — what worked

| Stage | Result |
|---|---|
| `docker compose config` with all 10 new `.env.example` placeholders | **Confirmed** — valid YAML with no interpolation error |
| `GET /health/ready` on all 9 application services | **Confirmed** — all returned `{"status":"ready","failures":[]}` after correcting the port assumption: `tool-service-renegotiation` exposes MCP on `:8400` and REST/health on `:8401` |
| Signed HMAC webhook → `whatsapp-bff` → Kafka → Orchestrator | **Confirmed** — `200 OK` on both turns |
| Orchestrator → Agent Runtime using new pair-specific JWT | **Confirmed** — both turns processed with `intent=renegociar_divida` |
| Agent Runtime → `conversation-memory-service` using its own pair | **Confirmed** — `GET /conversations/.../messages` → `200 OK` |
| Agent Runtime → `tool-service-renegotiation` via MCP pair JWT → `renegotiation-service` pair JWT → `core-bancario-mock` | **Confirmed** — `consultar_cliente` and `consultar_contratos` both returned `outcome=success` in turn 2, reconfirming the 19/07 same-turn policy fix under the new key model |
| Orchestrator → Memory/Audit through Outbox using pair JWTs | **Confirmed for turn 1** — `memory.append_message`, `memory.save_session`, `audit.record`, `kafka.intent_detected`, and `kafka.state_changed` were all `published` |
| Orchestrator → `whatsapp-bff` channel reply using pair JWT | **Reach confirmed**; Graph API rejected the synthetic number with `#131030`. `whatsapp-bff` returned `retryable:false` and the Orchestrator correctly parked the effect, preserving the 19/07 fix |
| **Zero authentication failures** in all nine service logs during the run | **Confirmed** — no `401`, `403`, `unknown_caller`, or `kid_sub_mismatch` outside deliberate negative tests |

## Negative tests

Manually forged PyJWT tokens were sent directly to `renegotiation-service` (`GET /clients/12345678900`):

| Scenario | Result |
|---|---|
| `kid: whatsapp-bff`, outside the service allowlist | **`401`** — rejected before signature verification |
| `kid: tool-service-renegotiation`, allowlisted but signed with the wrong secret | **`401`** — signature did not verify against the configured pair secret |

Both match the expected spec scenarios for unknown callers and wrong signatures.

## Finding — independent but blocking

**The Orchestrator Outbox permanently blocked later-turn effects when an earlier `channel.reply` had been parked as non-retryable.**

Turn 2 had six effects remain `pending` with `attempt_count=0` for more than four minutes because turn 1 contained a parked `channel.reply`. Root cause was the ordering predicate in `PostgresMessageInboxStore.cs`:

```sql
AND NOT EXISTS (
    SELECT 1 FROM ops.orchestrator_outbox predecessor
    WHERE predecessor.tenant_id = candidate.tenant_id
      AND predecessor.conversation_id = candidate.conversation_id
      AND predecessor.journey_version < candidate.journey_version
      AND predecessor.status <> 'published'
)
```

A parked effect remains `status='failed'`, which still satisfies `status <> 'published'` and therefore blocks every later version forever. This silently blocks unrelated audit and memory effects as well.

The problem was outside the secret-scoping change and was recorded for a dedicated follow-up: terminal parked failures need to count as resolved for ordering, unlike pending/publishing failures that are still active.

## Not verified in this run

- Asynchronous dispatch of turn-2 effects because it was blocked by the ordering finding above.
- Full handoff path.
- Test suites already confirmed by implementation agents were not rerun during this E2E validation.

## Conclusion

The pair-specific secret model works correctly end to end. Every observed synchronous and asynchronous call authenticated successfully under the new scheme, and negative tests confirmed rejection of unauthorized callers and incorrect secrets. The Outbox ordering finding is a real independent issue, not introduced by `per-service-internal-auth-secrets`.
