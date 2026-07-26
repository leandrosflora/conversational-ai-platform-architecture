# core-bancario-mock

Repo: [`leandrosflora/core-bancario-mock`](https://github.com/leandrosflora/core-bancario-mock) · Stack: .NET 8, Minimal API, processo único · Portas locais: `9401`–`9405`

## Responsabilidade

Mock das APIs bancárias externas usadas pelas jornadas de renegociação e cartão. As APIs de renegociação são consumidas via `renegotiation-service`; a Card API é consumida diretamente por `tool-service-cartao-credito`.

## APIs

| Porta | API | Endpoints |
|---|---|---|
| `9401` | ClientApi | `GET /clients/{cpf}` · `GET /clients/{clientId}/contracts` · `GET /contracts/{contractId}/debts` |
| `9402` | EligibilityApi | `GET /contracts/{contractId}/eligibility` |
| `9403` | ContractingApi | `POST /contracts/{contractId}/simulations` |
| `9404` | FormalizationApi | `POST /simulations/{simulationId}/confirmations` · `GET /agreements/{agreementId}/document` |
| `9405` | CardApi | `GET /clients/{cpf}/card/limit` · `GET /clients/{cpf}/card/invoice` |

Health e métricas:

```text
GET /health/live
GET /health/ready
GET /metrics
```

## Autenticação no ambiente integrado

O Compose habilita autenticação fail-closed no Core:

- HS256 com segredo distinto por caller/audiência;
- resolução da chave pelo `kid`;
- `kid == sub`;
- `iss`, `aud`, algoritmo, expiração e assinatura validados;
- `tenant_id` assinado deve ser UUID e igual ao `X-Tenant-Id`;
- APIs de renegociação aceitam somente `renegotiation-service`;
- Card API aceita somente `tool-service-cartao-credito`.

Health e métricas são públicos. Na execução isolada do repositório, auth permanece desabilitada por padrão e precisa ser habilitada explicitamente.

## Idempotência

As operações mutáveis exigem `Idempotency-Key`:

- simulação;
- confirmação.

Com mesma chave e request, o serviço devolve exatamente a resposta armazenada. A mesma chave com outro request retorna `409` não retryable; execução concorrente retorna `409` retryable.

O store do mock é em memória e é perdido no reinício. O `renegotiation-service` mantém sua própria idempotência durável em PostgreSQL, portanto o Core adiciona defesa em profundidade para homologação, mas não substitui persistência do sistema bancário real.

## CI e testes

O repositório executa restore, build e testes de integração. A suíte cobre:

- live/readiness;
- token ausente;
- caller permitido e negado por API;
- tenant mismatch;
- replay de simulação e confirmação;
- conflito de payload;
- ausência de chave idempotente.

## Dados

CPFs reservados fornecem cenários determinísticos. Não existe banco de dados real. IDs e replay idempotente existem apenas durante a vida do processo.

## Limitações

- idempotência process-local, sem persistência após reinício;
- HS256 simétrico, sem rotação automatizada;
- sem policy proof por estágio na Card API, pois as operações são somente leitura;
- sem datastore bancário real;
- valor de simulação ainda parte de uma base fixa de teste.

## Referências

- [Arquitetura de segurança](../security/security-architecture.md)
- [Roadmap de produção](../roadmap/production-readiness.md)
- [E2E multi-repositório](../runbook.md#11-e2e-multi-repositório)
