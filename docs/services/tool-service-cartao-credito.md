# tool-service-cartao-credito

Repo: [`leandrosflora/tool-service-cartao-credito`](https://github.com/leandrosflora/tool-service-cartao-credito) · Stack: Python, MCP (FastMCP) + FastAPI, Confluent.Kafka · Portas locais: `8410` (MCP), `8411` (REST/docs)

## Responsabilidade principal

Servidor MCP fino para a skill de fatura/limite de cartão de crédito, consumido por `agent-runtime-fatura-cartao`. Expõe duas tools MCP governadas e somente-leitura, que traduzem cada chamada numa requisição HTTP direta ao `core-bancario-mock` (Card API, `:9405`) e publicam um evento de auditoria (`tool.executed`) a cada execução. Deliberadamente mais simples que `tool-service-renegotiation`: como ambas as tools são consultas stateless de leitura, sem jornada multi-etapa nem ação irreversível, não há serviço intermediário de negócio nem gate de estágio de jornada — a política de autorização verifica apenas *qual serviço* pode chamar as tools.

## Dados que o serviço possui

Nenhum — é uma camada de tradução fina entre o protocolo MCP e o `core-bancario-mock`; não possui modelo de domínio próprio.

## APIs publicadas

Servidor MCP via streamable-HTTP em `/mcp` (porta `8410`). Duas tools expostas:

| Tool | Parâmetros | Endpoint HTTP chamado |
|---|---|---|
| `consultar_limite_cartao` | `cpf` | `GET {CORE_BANCARIO_BASE_URL}/clients/{cpf}/card/limit` |
| `consultar_fatura_cartao` | `cpf` | `GET {CORE_BANCARIO_BASE_URL}/clients/{cpf}/card/invoice` |

Ambas retornam um shape "não encontrado" fixo (`found: false`) se o CPF não resolver a cliente algum — distinto de `HasCard: false`, que indica um cliente real sem produto de cartão (reportado pelo próprio `core-bancario-mock`), para o agente poder diferenciar as duas respostas na conversa.

Há também um espelho REST (porta `8411`, contexto de execução assinado obrigatório) com as mesmas duas rotas (`GET /clients/{cpf}/card/limit`, `GET /clients/{cpf}/card/invoice`), além de `GET /health/live`, `GET /health/ready` e `GET /metrics`.

## Eventos publicados

| Tópico | Quando | Payload |
|---|---|---|
| `tool.executed` | Sempre, após cada chamada de tool (sucesso ou erro) | `tenant_id`, `tool_name`, `outcome` (`"success"`\|`"error"`), `correlation_id` |

O payload nunca inclui o `cpf` nem outros argumentos da tool — mesma prática de redação de `tool-service-renegotiation` para não vazar dado sensível no tópico de auditoria. Falha ao publicar é engolida (catch-log-continue).

## Eventos consumidos

Nenhum.

## Dependências síncronas

| Destino | Comportamento se indisponível |
|---|---|
| `core-bancario-mock` (`:9405`) | Chamada HTTP direta e **sem autenticação** (o `core-bancario-mock` não tem auth própria, diferente do `renegotiation-service`). Timeout de 5s por chamada; retry via `tenacity` (2 tentativas extras = 3 no total, 0.2s entre elas); um `404` (CPF não encontrado) é tratado como resultado de negócio normal, não entra no retry — retorna o shape "não encontrado"; qualquer outra falha após esgotar as tentativas levanta `CoreBancarioUnavailableError`, propagada ao agente cliente |

## Persistência & infraestrutura

Nenhuma. Sem estado — cada chamada de tool é uma tradução direta para uma requisição HTTP ao `core-bancario-mock`.

## Regras de negócio

1. **Autorização por serviço chamador**: só `agent-runtime-fatura-cartao` pode executar as tools governadas (`consultar_limite_cartao`, `consultar_fatura_cartao`) — verificado pelo `caller_service` do contexto de execução assinado; qualquer outro chamador recebe erro de política negada.
2. **Contexto de execução assinado obrigatório**: o JWT precisa ter `token_use == "tool_execution"` mais `sub`/`conversation_id`/`message_id` — sem isso, `403`.
3. Nenhum argumento de tool (CPF) é publicado no Kafka, em nenhuma circunstância.
4. Chamada ao `core-bancario-mock` não carrega segredo outbound — é o único downstream deste workspace chamado sem autenticação interna, por desenho.

## Referências de arquitetura

- [ADR 0003 — MCP para tool-calling governado](../adr/0003-mcp-governed-tool-calling.md)
- [Segurança da arquitetura](../security/security-architecture.md)
- [Diagramas de sequência da jornada](../architecture/sequence-diagrams.md)
