# conversation-orchestrator

Repo: [`leandrosflora/conversation-orchestrator`](https://github.com/leandrosflora/conversation-orchestrator) · Stack: .NET 8, Minimal API, PostgreSQL, Confluent.Kafka · Porta local (`dotnet run`): `8000` · Porta host via `docker compose up -d`: `5268` (ver [`runbook.md`](../runbook.md))

## Responsabilidade principal

Recebe uma mensagem inbound já normalizada pelo `whatsapp-bff` em `POST /messages` e a admite, de forma idempotente e ordenada, num Inbox transacional no PostgreSQL. Dentro dessa mesma transação de admissão, chama o agente de IA da skill ativa da conversa (roteando entre `agent-runtime-renegotiation` e `agent-runtime-fatura-cartao` via um `AgentSkillRegistry` configurável por tenant), decide o próximo `journey_stage` (uma string opaca que pertence à skill, não ao Orchestrator) e grava os efeitos colaterais daquele turno (resposta ao canal, projeção de memória, auditoria, handoff, eventos Kafka) numa Outbox durável — tudo na mesma transação Postgres. O endpoint responde `202`/`409` sem esperar nenhum desses efeitos serem de fato entregues; um `OutboxDispatcherService` em background é quem os publica de verdade, em ordem, com retry e backoff. Esta é a mudança arquitetural mais importante em relação a versões anteriores deste serviço: o pipeline deixou de ser síncrono de ponta a ponta.

## Dados que o serviço possui

O Orchestrator persiste diretamente em PostgreSQL (schema `ops`), diferente de versões anteriores em que não tinha banco próprio:

- `ops.message_inbox` — ledger de admissão/dedup por `(tenant_id, message_id)`: `status` (`processing`/`completed`/`failed`), `lease_until`, `attempt_count`, `completion_reason`, `source_received_at`.
- `ops.conversation_state` — estado corrente da conversa: `journey_stage` (**string opaca**, dona é a skill ativa, não um enum fechado do Orchestrator), `version`, `skill_id`, `structured_state` (jsonb, opaco), `last_intent`, `last_received_at`/`last_message_id` (usados para detectar mensagem atrasada), `processing_message_id`/`processing_lease_until` (lease por conversa), `session_started_at`. Colunas específicas de renegociação de uma versão anterior (`active_contract_id`, `active_simulation_id`, `active_agreement_id`) foram removidas — o design atual é deliberadamente agnóstico de skill.
- `ops.orchestrator_outbox` — fila de efeitos pendentes por turno: `effect_type`, `journey_version`, `idempotency_key`, `payload` (jsonb), `status` (`pending`/`publishing`/`published`/`failed`), `attempt_count`, `next_attempt_at`, `locked_until`.

## APIs publicadas

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/messages` | Admite uma mensagem inbound normalizada; retorna antes de qualquer efeito colateral ser entregue |

Requer `Authorization: Bearer <JWT interno>` e `X-Tenant-Id` batendo com a claim `tenant_id` assinada.

- `400 Bad Request` — `MessageId`/`From`/`ConversationId` vazios ou `ReceivedAt` default.
- `401` — JWT ausente/inválido/expirado (pipeline `JwtBearer` padrão).
- `403 Forbidden` — `X-Tenant-Id` não é UUID, ou não bate com a claim `tenant_id` do JWT.
- `202 Accepted`, corpo vazio — turno admitido normalmente **e** também o caso de mensagem já concluída/atrasada (`AlreadyCompleted`/late message) — indistinguíveis para quem chama.
- `409 Conflict` — mensagem ou conversa já em processamento (lease ativa); `{"error": "Message or conversation is already being processed. Retry after the active lease completes."}`.
- Exceção não tratada (ex.: guard de versão otimista falhando em `CompleteAsync`) propaga como `500` — o `whatsapp-bff` trata isso como falha e reencaminha pelo mecanismo de retry/DLQ dele.

## Eventos publicados

| Tópico | Quando | Payload |
|---|---|---|
| `intent.detected` | Quando o agente retorna um `Intent` não vazio | `ConversationId`, `Intent`, `Confidence`, `DetectedAt` |
| `conversation.state_changed` | Quando o `journey_stage` muda em relação ao anterior | `ConversationId`, `PreviousStage`, `NewStage`, `ChangedAt` |

Diferente de versões anteriores, esses eventos **não** são publicados de forma síncrona dentro do request: são efeitos da Outbox (`kafka.intent_detected`, `kafka.state_changed`), despachados depois pelo `OutboxDispatcherService`. Uma falha de publicação no Kafka não é mais "engolida e ignorada" — ela segue o retry/backoff normal da Outbox (ver "Regras de negócio") até publicar ou ser parqueada.

## Eventos consumidos

Nenhum. Não há `IConsumer` no processo — o `OutboxDispatcherService` é um `BackgroundService` que faz *poll* no PostgreSQL (`FOR UPDATE SKIP LOCKED` + um semáforo em processo sinalizado a cada admissão), não um consumer Kafka.

## Dependências síncronas

| Destino | Chamada | Timeout/retry | Comportamento se indisponível |
|---|---|---|---|
| `agent-runtime-renegotiation` (skill `renegotiation`, `:8100`) e `agent-runtime-fatura-cartao` (skill `cartao-credito`, `:8110`) | `POST /process` — um client HTTP nomeado por skill, mesma configuração para as duas | `AttemptTimeout=45s`, `TotalRequestTimeout=60s`, `CircuitBreaker.SamplingDuration=90s`, 2 retries/200ms | Nunca lança — degrada para `AgentRuntimeResult.Unavailable()`, que força `RequiresHandoff=true`, `HandoffReason="agent_runtime_unavailable"`. Essa chamada ainda é síncrona dentro do request (bloqueia a resposta a `/messages`), já que o turno não pode ser decidido sem ela |
| `whatsapp-bff` (`:5153`) | `POST /internal/messages` (efeito `channel.reply`/`channel.menu`, via Outbox) | Default 10s/30s, 2 retries/200ms | Resposta `{"retryable": false}` → `NonRetryableDispatchException`, efeito é parqueado imediatamente (dead-letter); qualquer outra falha segue o backoff normal da Outbox |
| `conversation-handoff-service` (`:8200`) | `POST /handoffs` (efeito `handoff.request`, via Outbox) | Default 10s/30s, 2 retries/200ms | Exceção propaga para o dispatcher → retry/backoff da Outbox |
| `conversation-audit-service` (`:8300`) | `POST /journey-events` (efeito `audit.record`, via Outbox) | Default 10s/30s, 2 retries/200ms | Idem |
| `conversation-memory-service` (`:8600`) | `POST /conversations/{id}/messages`, `PUT /sessions/{id}` (efeitos `memory.append_message`/`memory.save_session`, via Outbox) | Default 10s/30s, 2 retries/200ms | Idem — `GetOrCreateSessionAsync` (leitura de sessão) ainda existe no client mas não é mais chamado em lugar nenhum: o estado da conversa hoje vem só do checkpoint de `ops.conversation_state` |

Todos os cinco clientes anexam um JWT interno assinado por par (emissor, audiência) via `InternalTokenService`/`InternalRequestHandler` (ver "Regras de negócio").

**Gap conhecido**: a checagem de `/health/ready` (`ExpectedOutboundAudiences`) ainda só lista `agent-runtime-renegotiation` como audiência esperada — não inclui `agent-runtime-fatura-cartao`, então a falta/invalidez do segredo outbound dessa segunda skill não é pega pelo readiness probe.

## Persistência & infraestrutura

PostgreSQL (`ops.message_inbox`, `ops.conversation_state`, `ops.orchestrator_outbox`), criado/migrado de forma idempotente no startup. `NpgsqlDataSource` singleton, timeout de conexão/comando fixo em 5s. Kafka é usado só como saída (produtor + admin client para o readiness check) — sem consumer. `conversation-memory-service` (Redis/Mongo) continua guardando o espelho durável de histórico/sessão, mas hoje é só um destino de efeito da Outbox, não algo lido de forma síncrona durante o request.

## Regras de negócio

1. **Idempotência de admissão**: `(tenant_id, message_id)` é a chave única de `ops.message_inbox`. Reentrega de uma mensagem já `completed` retorna `202` sem reprocessar. Efeitos da Outbox têm uma segunda chave de idempotência, `(tenant_id, idempotency_key)` derivada de `{tenantId}:{messageId}` + prefixo por tipo de efeito, com `ON CONFLICT DO NOTHING` — mesmo um retry de `CompleteAsync` não duplica efeitos.
2. **Lease por conversa**: além do dedup por mensagem, existe uma lease de processamento por `(tenant_id, conversation_id)` em `ops.conversation_state` — duas mensagens da mesma conversa nunca processam em paralelo. Se uma segunda mensagem chega enquanto a lease está ativa, a linha do Inbox recém-adquirida é marcada `failed` (reclamável no próximo retry) e o endpoint responde `409`.
3. **Mensagem atrasada**: uma mensagem é considerada atrasada se sua tupla `(ReceivedAt, MessageId)` não for estritamente maior que a da última mensagem *concluída* daquela conversa. Mensagem atrasada é marcada `completed`/`completion_reason=late_message` sem chamar o agente e sem gerar efeitos — o endpoint responde `202` normalmente, indistinguível de um turno processado.
4. **Barreira de ordenação na Outbox**: efeitos de uma `journey_version` mais nova de uma conversa não são despachados enquanto existir um efeito não publicado de uma versão anterior da mesma conversa — a menos que esse efeito anterior já tenha sido parqueado (dead-letter, `next_attempt_at` empurrado para além de 1 dia). Isso garante que o cliente nunca veja a resposta do turno N+1 antes da do turno N, mas um efeito genuinamente travado (ainda tentando, não parqueado) bloqueia todos os turnos seguintes daquela conversa por até ~20 tentativas/backoff exponencial (máx. 300s por tentativa).
5. **Roteamento multi-skill**: cada tenant tem uma lista de skills habilitadas (`AgentSkillOptions.TenantSkillAssignments`); hoje o tenant padrão tem `renegotiation` e `cartao-credito`. Com 1 skill só, ela é fixada automaticamente, sem menu. Com 2+, a skill fica "pinada" na conversa (`skill_id` em `conversation_state`) até: (a) o cliente responder um botão de menu diferente, (b) a sessão expirar (15 min, ver regra 7), ou (c) o agente responder `OutOfScope=true` — nesse caso a skill é despinada e o menu de seleção é reapresentado (a menos que o tenant só tenha 1 skill, caso em que vira handoff com motivo `out_of_scope_no_alternative_skill`).
6. **Skill não configurada**: se a skill pinada/selecionada não existir mais no catálogo (`AgentSkillOptions.Skills`), ou o tenant não tiver skill nenhuma atribuída, o turno vira handoff com motivo `skill_not_configured` — mesmo tratamento dado a um Agent Runtime indisponível.
7. **Janela de sessão de 15 minutos**, ancorada no início da sessão (`SessionStartedAt`), não na última atividade. Ao expirar: `journey_stage`/`structured_state` resetam para um estado limpo, a skill é despinada (reabre o menu se o tenant tiver 2+ skills), e o agente recebe `SessionReset=true` para poder avisar o cliente explicitamente em vez de silenciosamente perguntar de novo.
8. **Estados reservados que o Orchestrator conhece** (o resto do `journey_stage` é opaco, pertence à skill): `Started` (toda conversa nova) e `HandoffRequested`/`AwaitingSkillSelection` — esses dois últimos deliberadamente **não** são repassados como `State` ao agente numa próxima chamada, correção de um bug real em que o tool-service da skill negava toda tool call ao ver `AwaitingSkillSelection` como se fosse o próprio estágio de jornada da skill.
9. **Auth JWT em `/messages`**: emissor/audiência/assinatura validados via chave simétrica por `kid` (`InternalAuth:InboundSecrets`), com checagem extra de que `kid == sub` na claim (evita um serviço apresentar um token assinado com a chave de outro). Além disso, o header `X-Tenant-Id` precisa bater com a claim `tenant_id` do próprio token — dupla checagem.
10. **Auth JWT de saída**: cada chamada às cinco famílias de dependência síncrona carrega um JWT HS256 de curta duração (30–900s, default 300s) assinado com o segredo específico daquele par (emissor, audiência) em `InternalAuth:OutboundSecrets` — não um segredo único compartilhado. Para as duas skills de agente, a audiência usada é o nome do serviço downstream configurado por skill (`agent-runtime-renegotiation`/`agent-runtime-fatura-cartao`), cada uma com seu próprio segredo.

## Referências de arquitetura

- [ADR 0002 — Hexagonal / ports-and-adapters nos serviços .NET](../adr/0002-hexagonal-ports-and-adapters.md)
- [ADR 0004 — Resiliência catch-log-continue](../adr/0004-catch-log-continue-resilience.md)
- [ADR 0005 — Outbox transacional, tools governadas e ordenação](../adr/0005-transactional-outbox-governed-tools-and-ordering.md)
- [Diagramas de sequência da jornada](../architecture/sequence-diagrams.md)
