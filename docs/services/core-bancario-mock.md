# core-bancario-mock

Repo: [`leandrosflora/core-bancario-mock`](https://github.com/leandrosflora/core-bancario-mock) · Stack: .NET 8, Minimal API, processo único · Portas locais: `9401`–`9405`

!!! danger "Componente exclusivo de demonstração e homologação"
    Este serviço não representa um Core Bancário produtivo e não contém dados reais. Todos os clientes, contratos, débitos, propostas, acordos, limites e faturas são sintéticos. Nenhuma resposta deste serviço deve ser interpretada como informação financeira válida, e nenhuma confirmação cria obrigação, contrato ou lançamento real.

## Responsabilidade

Mock das APIs bancárias externas usadas pelas jornadas de renegociação e cartão. As APIs de renegociação são consumidas via `renegotiation-service`; a Card API é consumida diretamente por `tool-service-cartao-credito`.

Sua finalidade é permitir testes determinísticos de:

- contratos de API;
- autenticação e autorização entre workloads;
- isolamento por tenant;
- idempotência;
- estados de jornada;
- tratamento de erros;
- observabilidade e E2E multi-repositório.

Ele não valida regras financeiras corporativas, qualidade de dados produtivos ou aderência a produtos bancários reais.

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

## Arquitetura-alvo

Em uma implantação corporativa, cada grupo de endpoints deve ser substituído por APIs reais dos sistemas responsáveis:

| Mock atual | Destino esperado na arquitetura-alvo |
|---|---|
| ClientApi | Cadastro e visão de cliente autorizada |
| Contratos e débitos | Sistema de contratos, cobrança ou recuperação |
| EligibilityApi | Motor corporativo de elegibilidade/política |
| ContractingApi | Motor de simulação e condições financeiras |
| FormalizationApi | Contratação, formalização e gestão documental |
| CardApi | Processadora ou plataforma real do domínio de cartões |

A substituição não deve ser uma simples troca de URL. Deve incluir contratos versionados, autenticação de workload, autorização por operação, idempotência persistente, tratamento de concorrência, SLA, auditoria, classificação de dados e homologação com massas não produtivas.

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

Esses testes comprovam comportamento técnico do mock e dos consumidores. Eles não comprovam cálculo financeiro, elegibilidade produtiva, saldo real ou formalização bancária real.

## Dados

CPFs reservados fornecem cenários determinísticos. Não existe banco de dados real. IDs e replay idempotente existem apenas durante a vida do processo.

Características dos dados:

- totalmente sintéticos;
- sem vínculo com pessoas reais;
- sem origem em ambiente produtivo;
- valores gerados para cenários de teste;
- adequados somente para desenvolvimento, demonstração, CI e homologação técnica.

## Limitações

- idempotência process-local, sem persistência após reinício;
- HS256 simétrico, sem rotação automatizada;
- sem policy proof por estágio na Card API, pois as operações são somente leitura;
- sem datastore bancário real;
- valor de simulação ainda parte de uma base fixa de teste;
- regras de elegibilidade e contratação simplificadas;
- ausência de conciliação, contabilização, liquidação e confirmação de pagamento;
- indisponível para qualquer uso produtivo.

## Referências

- [Contexto de negócio](../context/business-context.md)
- [Mapa de domínios](../functional/domain-map.md)
- [Arquitetura de segurança](../security/security-architecture.md)
- [Roadmap de produção](../roadmap/production-readiness.md)
- [E2E multi-repositório](../runbook.md#11-e2e-multi-repositório)