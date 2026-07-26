# core-bancario-mock

Repo: [`leandrosflora/core-bancario-mock`](https://github.com/leandrosflora/core-bancario-mock) · Stack: .NET 8, Minimal API, processo único · Portas locais: `9401`–`9405`

## Responsabilidade principal

Mock, num único processo (`builder.WebHost.UseUrls(...)` escutando em 5 portas simultaneamente), das APIs bancárias externas que as duas skills do workspace assumem existir: 4 APIs de renegociação consumidas via `renegotiation-service` (consulta de cliente/contratos/dívidas, elegibilidade, contratação/simulação e formalização) e uma 5ª API de cartão de crédito (limite e fatura) consumida diretamente por `tool-service-cartao-credito`. Sem persistência — dados de qualquer CPF fora das tabelas de cenários abaixo são gerados inline a cada chamada.

## Dados que o serviço possui

Nenhuma persistência real, mas dois conjuntos fixos de CPFs reservados:
- **Renegociação** (`ScenarioFixtures.ByCpf`): 10 CPFs de dígito repetido 11x (`00000000000` a `99999999999`, mais um CPF de teste manual `12345678911`) resolvem para dados determinísticos de cliente/contratos/dívidas/elegibilidade/simulação/formalização, cobrindo os cenários de negócio da renegociação (inelegibilidade, múltiplos contratos, sem dívida em aberto, simulação que expira, documento pendente etc.) — ver `openspec/changes/validate-renegotiation-flow-scenarios/design.md` e `conversational-ai-demo-arch/docs/homologacao/massa-de-teste-clientes.md`.
- **Cartão de crédito** (`CardFixtures.ByCpf`): 4 CPFs reservados cobrem os cenários da skill de fatura/limite — `11111111111` (fluxo feliz), `22222222222` (limite quase esgotado, fatura fechada), `66666666666` (cliente sem cartão, `HasCard:false`), `77777777777` (fatura zerada). Qualquer outro CPF válido recebe um fallback genérico determinístico (não aleatório) derivado do próprio CPF.

Qualquer CPF fora dessas listas continua com dado gerado inline a cada chamada (`ContractSummary`, `DebtItem` com valores fixos; IDs de simulação/acordo via `Guid.NewGuid()`).

## APIs publicadas

| Porta | API | Endpoints |
|---|---|---|
| `9401` | ClientApi | `GET /clients/{cpf}` · `GET /clients/{clientId}/contracts` · `GET /contracts/{contractId}/debts` |
| `9402` | EligibilityApi | `GET /contracts/{contractId}/eligibility` |
| `9403` | ContractingApi | `POST /contracts/{contractId}/simulations` |
| `9404` | FormalizationApi | `POST /simulations/{simulationId}/confirmations` · `GET /agreements/{agreementId}/document` |
| `9405` | CardApi | `GET /clients/{cpf}/card/limit` · `GET /clients/{cpf}/card/invoice` — recebe tenant/JWT de `tool-service-cartao-credito`, mas como as 4 APIs acima, não os valida; consumida diretamente por `tool-service-cartao-credito`, não pelo `renegotiation-service` |

## Eventos publicados / consumidos

Nenhum — sem Kafka.

## Dependências síncronas

Nenhuma — é o "fim da linha" da cadeia de chamadas.

## Persistência & infraestrutura

Nenhuma. Roda tanto via `dotnet run` local quanto em container (tem `Dockerfile`, usado como `build: context: ../core-bancario-mock` no `docker-compose.yml` deste repo).

## Regras de negócio (gatilhos de teste, verificados no código)

Genéricos, aplicados a qualquer CPF fora da tabela de cenários reservados (ver "Dados que o serviço possui" acima):

| Cenário | Gatilho exato | Resposta |
|---|---|---|
| Cliente não encontrado | `cpf == "00000000000"` | **`404 Not Found`** |
| Contrato não elegível | `contractId` contém `"inelegivel"` (case-insensitive) | `200 OK`, `{eligible:false, reason:"cliente_inadimplente_critico"}` |
| Simulação não possível | `installments <= 0` ou `> 48` | `200 OK`, `{possible:false, reason:"installments_out_of_range"}` |
| Confirmação não possível | `simulationId` contém `"expired"` | `200 OK`, `{confirmed:false, reason:"simulation_expired"}` |
| Documento não disponível | `agreementId` contém `"pendente"` | `200 OK`, `{available:false, reason:"document_not_ready"}` |

Para os 10 CPFs reservados, elegibilidade/simulação-expira/documento-pendente vêm de dados fixos por
CPF em vez desses gatilhos textuais (embora `simulationId`/`agreementId` ainda carreguem os mesmos
marcadores `-expired`/`-pendente` internamente, propagados a partir do CPF do contrato de origem).

**Convenção de status HTTP:** "não encontrado" (o identificador não resolve a nada real, ex. `GET /clients/{cpf}` com CPF não cadastrado) sempre retorna `404 Not Found`; "negócio negativo" (o identificador resolve a algo real que foi avaliado e reprovado — os 4 cenários de inelegibilidade/simulação/confirmação/documento acima) sempre retorna `200 OK` com um campo de resultado indicando o motivo.

**Gap conhecido:** os endpoints de contratos e dívidas (`/clients/{clientId}/contracts`, `/contracts/{contractId}/debts`) não implementam nenhum gatilho de "não encontrado" próprio, embora o `renegotiation-service` os trate como se pudessem retornar 404.

## Referências de arquitetura

- [Matriz de datastores](../contracts/data-stores.md)
