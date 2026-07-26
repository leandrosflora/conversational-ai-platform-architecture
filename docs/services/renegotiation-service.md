# renegotiation-service

Repo: [`leandrosflora/renegotiation-service`](https://github.com/leandrosflora/renegotiation-service) · Stack: .NET 8, Minimal API · Porta local (`dotnet run`): `9400` · Porta host via `docker compose up -d`: `5266`

## Responsabilidade principal

Gateway HTTP que unifica, sob uma API REST própria, as 4 APIs do Core Bancário (mockadas em `core-bancario-mock`): consulta de cliente/contratos/dívidas, elegibilidade, simulação e formalização. **Não contém regra de negócio de crédito própria** — cada use case apenas chama o client outbound correspondente e repassa o resultado (pass-through). As regras de negócio "de renegociação" (o que torna um contrato inelegível, os limites de parcelamento, etc.) vivem no `core-bancario-mock`, não aqui.

## Dados que o serviço possui

Modelos de wire (`ClientLookupResult`, `ContractsResult`, `DebtsResult`, `EligibilityResult`, `SimulationResult`, `AgreementConfirmationResult`, `DocumentResult`) — não são dados de domínio próprios. Há, no entanto, um estado real persistido: um registro de idempotência por simulação em PostgreSQL (`PostgresSimulationIdempotencyStore`, ver "Persistência").

## APIs publicadas

| Método | Rota | Chama (core-bancario-mock) |
|---|---|---|
| `GET` | `/clients/{cpf}` | ClientApi `:9401` |
| `GET` | `/clients/{clientId}/contracts` | ClientApi `:9401` |
| `GET` | `/contracts/{contractId}/debts` | ClientApi `:9401` |
| `GET` | `/contracts/{contractId}/eligibility` | EligibilityApi `:9402` |
| `POST` | `/contracts/{contractId}/simulations` | ContractingApi `:9403` |
| `POST` | `/simulations/{simulationId}/confirmations` | FormalizationApi `:9404` |
| `GET` | `/agreements/{agreementId}/document` | FormalizationApi `:9404` |

`POST /contracts/{contractId}/simulations` e `POST /simulations/{simulationId}/confirmations` exigem header `Idempotency-Key` (`400` se ausente) e um JWT `governed_tool` assinado por `tool-service-renegotiation` (ver "Regras de negócio") — `403` se a validação do contexto assinado falhar. `POST /contracts/{contractId}/simulations` também pode responder `409 Conflict`: `retryable:true` se outra simulação com a mesma chave ainda está em andamento, `retryable:false` se a mesma chave já foi usada com parâmetros diferentes.

## Eventos publicados / consumidos

Nenhum. Não há Kafka neste serviço — é puramente síncrono, request/response HTTP.

## Dependências síncronas

As 4 APIs do `core-bancario-mock`, cada uma com `HttpClient` tipado + resilience handler (2 retries configuráveis por API).

## Persistência & infraestrutura

**PostgreSQL** (`PostgresSimulationIdempotencyStore`): uma linha por `Idempotency-Key` de simulação, guardando o hash canônico da requisição e a resposta obtida do Core Bancário — uma chave repetida com o mesmo request devolve a resposta persistida sem chamar o Core Bancário de novo; repetida com um request diferente é rejeitada. Fora isso, sem outro banco — toda a demais informação vem das chamadas HTTP síncronas ao Core Bancário mock.

## Regras de negócio

1. **Idempotência de simulação**: `Idempotency-Key` nova executa e persiste a resposta; chave já concluída retorna a mesma resposta sem chamar o Core Bancário de novo (`IdempotencyInProgressException`/`IdempotencyConflictException` distinguem, respectivamente, uma chave ainda em processamento de uma chave reutilizada com parâmetros diferentes).
2. **Defesa em profundidade da policy por estágio de jornada**: cada endpoint de simulação/confirmação revalida, de forma independente do `tool-service-renegotiation`, o JWT `governed_tool` recebido (`GovernedToolPolicy.TryAuthorize`) — confere `sub == "tool-service-renegotiation"`, `token_use == "governed_tool"`, `tool_name` bate com a operação chamada, todas as claims de contexto (`tenant_id`, `conversation_id`, `message_id`, `journey_stage`, `journey_version`, `policy_id`) presentes, `journey_stage` dentro do allowlist específico daquele endpoint (espelha `tool-service-renegotiation`'s `SIMULATION_STAGES`/`CONFIRMATION_STAGES`, não apenas confia no que o chamador já validou), e que o `Idempotency-Key` do header bate exatamente com a claim `policy_id` assinada. Qualquer falha nessa revalidação retorna `403`.
3. **Confirmação exige evidência assinada**: `POST /simulations/{simulationId}/confirmations` exige adicionalmente que `confirmation_message_id` esteja presente e seja igual ao `message_id` do próprio contexto assinado.
4. Qualquer resposta HTTP 2xx do Core Bancário — mesmo representando um desfecho negativo de negócio (`eligible:false`, `possible:false`, `confirmed:false`, `available:false`) — é repassada como `200 OK` pelo `renegotiation-service`. Isso é uma convenção de mapeamento de erro, não uma regra de crédito própria — as regras de elegibilidade/limites vivem no `core-bancario-mock`.
5. Só existe `502 Bad Gateway` quando a chamada ao Core Bancário genuinamente falha (timeout, conexão recusada) — capturado via `UpstreamServiceUnavailableException`, tratado por `try/catch` em cada endpoint (não é middleware global).
6. Um CPF não encontrado no ClientApi (404) é mapeado para `ClientLookupResult(Found: false)` — mas isso só funciona porque o cliente HTTP interpreta 404 como "não encontrado"; **os endpoints de contratos/dívidas (`GetContractsUseCase`/`GetDebtsUseCase`) também tratam esse caso, mas o mock atual não implementa 404 para essas duas rotas** — gap conhecido entre o client e o mock, ver [`docs/services/core-bancario-mock.md`](core-bancario-mock.md).

## Referências de arquitetura

- [ADR 0002 — Hexagonal / ports-and-adapters nos serviços .NET](../adr/0002-hexagonal-ports-and-adapters.md)
- [Matriz de datastores](../contracts/data-stores.md)
