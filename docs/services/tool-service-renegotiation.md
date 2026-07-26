# tool-service-renegotiation

Repo: [`leandrosflora/tool-service-renegotiation`](https://github.com/leandrosflora/tool-service-renegotiation) · Stack: Python, MCP (FastMCP) + FastAPI, Confluent.Kafka · Portas locais: `8400` (MCP), `8401` (REST mirror)

## Responsabilidade principal

Servidor MCP que expõe, como ferramentas governadas, as operações do fluxo de renegociação — traduzindo cada chamada de tool numa requisição HTTP ao `renegotiation-service` e publicando um evento de auditoria (`tool.executed`) a cada execução, com ou sem sucesso.

## Dados que o serviço possui

Nenhum — é uma camada de tradução fina entre o protocolo MCP e o `renegotiation-service`; não possui modelo de domínio próprio.

## APIs publicadas

Servidor MCP via streamable-HTTP em `/mcp` (porta `8400`), **mais um espelho REST completo** das mesmas sete operações na porta `8401` (mesmas rotas do `renegotiation-service`, ex. `GET /clients/{cpf}`, `POST /contracts/{contractId}/simulations`) — contexto de execução assinado também obrigatório nesse caminho. Sete tools MCP expostas:

| Tool | Parâmetros | Endpoint HTTP chamado |
|---|---|---|
| `consultar_cliente` | `cpf` | `GET /clients/{cpf}` |
| `consultar_contratos` | `client_id` | `GET /clients/{client_id}/contracts` |
| `consultar_debitos` | `contract_id` | `GET /contracts/{contract_id}/debts` |
| `validar_elegibilidade` | `contract_id` | `GET /contracts/{contract_id}/eligibility` |
| `simular_proposta` | `contract_id, installments, discount_percentage=0.0` | `POST /contracts/{contract_id}/simulations` |
| `confirmar_acordo` | `simulation_id` | `POST /simulations/{simulation_id}/confirmations` |
| `gerar_documento` | `agreement_id` | `GET /agreements/{agreement_id}/document` |

## Eventos publicados

| Tópico | Quando | Payload |
|---|---|---|
| `tool.executed` | Sempre, em `finally`, após cada chamada de tool (sucesso ou erro) | `tool_name`, `outcome` (`"success"`\|`"error"`), `correlation_id` |

**Importante:** o payload nunca inclui os argumentos da tool (CPF, IDs de contrato/simulação/acordo) — não é mascaramento, é exclusão total, por desenho ("payload intentionally never includes tool arguments... so there is no raw sensitive identifier to leak into the audit trail"). Falha ao publicar é engolida (catch-log-continue).

## Eventos consumidos

Nenhum.

## Dependências síncronas

| Destino | Comportamento se indisponível |
|---|---|
| `renegotiation-service` (`:9400`) | Timeout de 5s por chamada; retry via `tenacity` (2 tentativas extras = 3 no total, 0.2s entre elas); se todas falharem, levanta `RenegotiationServiceUnavailableError` **sem** incluir a mensagem original do erro (evita vazar URL/CPF no log) — a exceção sobe e o FastMCP a converte em `ToolError` para o agente cliente |

## Persistência & infraestrutura

Nenhuma. Sem estado — cada chamada de tool cria um `httpx.AsyncClient` novo (sem connection pooling persistente entre chamadas).

## Regras de negócio

1. Nenhum argumento de tool (dado potencialmente sensível como CPF) é publicado no Kafka, em nenhuma circunstância.
2. Falha de rede/timeout ao chamar o `renegotiation-service` não é capturada como retorno estruturado — vira exceção MCP (`ToolError`) propagada ao agente, não um `{"error": ...}` dentro de um resultado de sucesso.
3. O log de erro do client HTTP registra apenas o tipo da exceção, nunca a mensagem/URL completa (mesmo motivo de proteção de dados sensíveis).
4. **Policy de autorização por estágio de jornada** (`app/policy.py`), aplicada a toda chamada de tool (MCP ou REST) via `authorize_tool`: só `agent-runtime-renegotiation` pode chamar (`caller_service` do contexto assinado); cada tool de leitura (`consultar_cliente`, `consultar_contratos`, `consultar_debitos`, `validar_elegibilidade`) só é permitida a partir de um allowlist de `journey_stage`s específico (inclui deliberadamente `Started`/estágios iniciais, já que a claim de estágio é assinada uma vez por turno e não avança no meio dele, e inclui `HandoffRequested` para não travar permanentemente uma conversa reaberta pelo bot); `simular_proposta` exige estágio em `SIMULATION_STAGES` e todos os três argumentos (`contract_id`, `installments`, `discount_percentage`); `gerar_documento` só a partir de `AgreementConfirmed`/`DocumentAvailable`/`Completed`.
5. **`confirmar_acordo`** exige, além do estágio (`ProposalSelected`/`ConfirmationPending`), evidência de confirmação explícita: `confirmation_message_id` presente e igual ao `message_id` da mensagem atual — nunca uma confirmação "herdada" de um turno anterior.
6. **Chave de idempotência determinística**: `simular_proposta` deriva sua `Idempotency-Key` de um hash SHA-256 de `(tenant_id, conversation_id, message_id, journey_version, contract_id, installments, discount_percentage)`; `confirmar_acordo` deriva a dela de `(tenant_id, conversation_id, confirmation_message_id, simulation_id)` — repassadas ao `renegotiation-service`, que é quem de fato garante a idempotência (ver [renegotiation-service](renegotiation-service.md)).

## Referências de arquitetura

- [ADR 0003 — MCP para tool-calling governado](../adr/0003-mcp-governed-tool-calling.md)
- [Segurança da arquitetura](../security/security-architecture.md)
- [Diagramas de sequência da jornada](../architecture/sequence-diagrams.md)
