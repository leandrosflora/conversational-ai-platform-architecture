# agent-runtime-fatura-cartao

Repo: [`leandrosflora/agent-runtime-fatura-cartao`](https://github.com/leandrosflora/agent-runtime-fatura-cartao) · Stack: Python, FastAPI, Strands Agents, OpenAI · Porta local: `8110`

## Responsabilidade principal

Hospeda o agente de IA (Strands Agents + OpenAI) que responde, via WhatsApp, perguntas do cliente sobre o cartão de crédito: limite total, limite disponível e valor atual da fatura. Recebe uma mensagem do Orchestrator em `POST /process`, conecta-se ao `tool-service-cartao-credito` via MCP, monta o agente e o invoca. Deliberadamente mais simples que `agent-runtime-renegotiation`: não há jornada multi-estágio (contratos/simulações/acordos) — apenas identificação do cliente por CPF seguida de consultas de leitura.

## Dados que o serviço possui

Nenhum modelo persistido — `ProcessRequest`/`ProcessResponse` (Pydantic, `app/models.py`) são contratos de wire. O único "estado" (o CPF já identificado) é opaco, trafega no campo `StructuredState` trocado com o `conversation-orchestrator`, e não é persistido em banco/cache próprio do serviço.

## APIs publicadas

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/process` | Processa uma mensagem e devolve a decisão do agente |

Request (`ProcessRequest`, PascalCase — espelha o que o Orchestrator envia): `TenantId`, `ConversationId`, `MessageId`, `MessageType`, `Text?`, `State?`, `JourneyVersion?`, `LastIntent?`, `StructuredState?` (dict opaco, chave `cpf`), `SessionReset?`, `SessionStartedAt?`.
Response (`ProcessResponse`, PascalCase): `Intent?`, `Confidence` (default `0.0`), `ReplyText?`, `RequiresHandoff` (default `false`), `HandoffReason?`, `State` (`Started`/`CustomerIdentified`), `StructuredState?` (`{"cpf": "..."}` uma vez identificado), `OutOfScope` (`true` quando a pergunta não é sobre limite/fatura — sinaliza ao orquestrador para resetar o menu de skills).

Erros: `400` se o payload `TenantId` não bater com o `X-Tenant-Id`/claim já resolvidos; `403` se a claim `tenant_id` assinada estiver ausente ou não bater com o header `X-Tenant-Id` (checado antes do payload); `401` sem JWT interno válido/expirado; `422` se campos obrigatórios faltarem.

## Eventos publicados

| Tópico | Quando | Payload | Falha é engolida? |
|---|---|---|---|
| `agent.events` | Sempre, ao final de cada `/process` bem-sucedido | `tenant_id`, `conversation_id`, `intent`, `confidence`, `requires_handoff`, `handoff_reason` | Sim — `try/except` ao redor da publicação apenas loga erro, nunca derruba a requisição |

O payload não inclui `cpf` nem o texto do cliente.

## Eventos consumidos

Nenhum.

## Dependências síncronas

| Destino | Protocolo | Comportamento se indisponível |
|---|---|---|
| OpenAI (`gpt-4o-mini` por padrão) | SDK Strands, via `OpenAIModel` | Timeout de 45s (`asyncio.wait_for`) → `requires_handoff=true`, `handoff_reason="agent_runtime_timeout"`. Qualquer outra exceção → `requires_handoff=true`, `handoff_reason="agent_runtime_unavailable"`. Sem retry/tenacity — degrada direto para handoff. **Só é chamada quando `MOCK_AGENT_ENABLED=false`** — no `docker-compose.yml` deste repositório o default é `${MOCK_AGENT_ENABLED:-true}`, então por padrão o ambiente local usa `app/agent/mock.py` (decisão determinística por palavra-chave) e nunca invoca a OpenAI de verdade, mesma convenção do `agent-runtime-renegotiation` |
| `tool-service-cartao-credito` (`:8410`, MCP) | streamable-HTTP, via `strands.tools.mcp.MCPClient`, token assinado por requisição (`token_use: tool_execution`) | Se a conexão/listagem de tools falhar, o agente segue sem essas tools (não bloqueia o request), apenas loga warning |

Não chama `conversation-memory-service` nem `knowledge-service` (diferente de `agent-runtime-renegotiation`).

## Persistência & infraestrutura

Nenhuma persistência própria. Observabilidade via OpenTelemetry (traces OTLP para `jaeger:4317`) e métricas Prometheus (`AGENT_REQUESTS`, `AGENT_HANDOFFS`, `AGENT_DURATION`).

## Regras de negócio

1. **Guard determinístico de CPF**: o agente nunca chama `consultar_limite_cartao`/`consultar_fatura_cartao` com um CPF que o cliente não tenha literalmente informado nesta conversa — bloqueado por um hook `BeforeToolCallEvent`, não apenas por instrução de prompt. Candidatos de CPF são extraídos do texto por regex, excluindo matches que parecem número de telefone.
2. **Threshold de confiança = 0.6** (configurável): força `requires_handoff=true` se `confidence` ficar abaixo do threshold — mas só quando `out_of_scope` é `false` (baixa confiança numa resposta out-of-scope não vira handoff).
3. Falha total do LLM (timeout, sem credenciais etc.) nunca vira erro HTTP — degrada para uma decisão de handoff.
4. Falha ao conectar no Tool Service MCP não bloqueia o processamento — o agente simplesmente não tem acesso a essas tools naquele turno.
5. Falha ao publicar em Kafka nunca falha o request.
6. **`out_of_scope`**: sinaliza `true` quando a pergunta não é sobre limite/fatura (ex.: renegociação de dívida, PIX) — permite ao `conversation-orchestrator` resetar e reexibir o menu de seleção de skill.
7. **`session_reset`**: se a sessão anterior expirou (>15 min), o agente informa isso ao cliente e repede o CPF mesmo que já tenha sido informado antes.

## Referências de arquitetura

- [ADR 0003 — MCP para tool-calling governado](../adr/0003-mcp-governed-tool-calling.md)
- [ADR 0004 — Resiliência catch-log-continue](../adr/0004-catch-log-continue-resilience.md)
- [Diagramas de sequência da jornada](../architecture/sequence-diagrams.md)
