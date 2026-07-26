# core-bancario-mock

Repo: [`leandrosflora/core-bancario-mock`](https://github.com/leandrosflora/core-bancario-mock) · Stack: .NET 8, Minimal API, processo único · Portas locais: `9401`–`9405`

## Responsabilidade principal

Mock, num único processo, das APIs bancárias externas usadas pelas jornadas de renegociação e cartão. As quatro APIs de renegociação são consumidas via `renegotiation-service`; a Card API é consumida diretamente por `tool-service-cartao-credito`.

O repositório possui workflow de CI com restore e build. Ainda não possui projeto de testes automatizados, health endpoints dedicados, persistência de idempotência nem middleware de autenticação na ponta receptora.

## Dados

Não há persistência. CPFs reservados fornecem cenários determinísticos e CPFs válidos não reservados recebem fallback determinístico. IDs de simulação e acordo ainda são gerados por chamada.

## APIs

| Porta | API | Endpoints |
|---|---|---|
| `9401` | ClientApi | `GET /clients/{cpf}` · `GET /clients/{clientId}/contracts` · `GET /contracts/{contractId}/debts` |
| `9402` | EligibilityApi | `GET /contracts/{contractId}/eligibility` |
| `9403` | ContractingApi | `POST /contracts/{contractId}/simulations` |
| `9404` | FormalizationApi | `POST /simulations/{simulationId}/confirmations` · `GET /agreements/{agreementId}/document` |
| `9405` | CardApi | `GET /clients/{cpf}/card/limit` · `GET /clients/{cpf}/card/invoice` |

## Autenticação e idempotência

Estado atual:

- a Card API recebe `Authorization` e `X-Tenant-Id`, mas não valida;
- as APIs de renegociação recebem os headers encaminhados pelo `renegotiation-service`, mas o mock não os aplica como controle;
- o mock não persiste `Idempotency-Key`;
- simulação e confirmação podem gerar novos IDs em repetição.

Próximo passo obrigatório:

1. validar assinatura, `iss`, `sub`, `aud`, `kid`, expiração e tenant;
2. restringir callers por API;
3. persistir chave, hash canônico e resposta;
4. retornar replay idempotente ou conflito;
5. adicionar testes de autorização e concorrência.

## Convenção HTTP

- identificador malformado ou cliente não encontrado: `404`;
- resultado de negócio negativo: `200` com campo de resultado e motivo;
- indisponibilidade técnica futura: `5xx`;
- autenticação ausente/inválida após o hardening: `401`/`403`.

## Infraestrutura

O serviço roda via `dotnet run` ou container. O CI atual é build-only até a criação de um projeto de testes. No Compose, a verificação E2E usa temporariamente `GET /clients/11111111111` como sinal de disponibilidade; `/health/live` e `/health/ready` devem substituí-lo.

## Referências

- [Arquitetura de segurança](../security/security-architecture.md)
- [Roadmap de produção](../roadmap/production-readiness.md)
