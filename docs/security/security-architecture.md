# Arquitetura de segurança — estado implementado

Este documento descreve os controles do change set coordenado entre o repositório de arquitetura e os serviços. A arquitetura-alvo permanece em `docs/architecture/C4/c4-container-target.puml`.

## 1. Fronteiras de confiança

| Fronteira | Controle implementado |
|---|---|
| WhatsApp → BFF | verify token e HMAC-SHA256 sobre os bytes originais |
| Serviço → serviço | JWT HS256 curto, segredo distinto por par emissor/audiência |
| Tenant → serviço | UUID canônico na claim `tenant_id` e em `X-Tenant-Id` |
| Agent Runtime → Tool Service | token `tool_execution` e allowlist do caller |
| Tool Service de renegociação → domínio | token `governed_tool`, tool/estágio e `policy_id` ligados à operação |
| Renegotiation Service → Core | JWT de serviço, tenant e `Idempotency-Key`; Core restringe caller e deduplica |
| Tool Service de cartão → Core | JWT de serviço e tenant; Core restringe caller; operações somente leitura |
| Entrada → negócio | Kafka confirmado antes do ACK; Inbox/estado transacionais |
| Side effects | Outbox durável, replay at-least-once e deduplicação no destino |
| Dados | chaves, queries e índices tenant-scoped |

## 2. Webhook

`whatsapp-bff` valida:

- `hub.verify_token` no handshake;
- `X-Hub-Signature-256` no POST;
- HMAC-SHA256 calculado sobre o body original;
- rejeição antes do parsing de negócio ou publicação Kafka.

O webhook é público por necessidade do provedor. Endpoints internos exigem JWT, tenant assinado e, quando mutáveis, chave idempotente.

## 3. Identidade interna

Claims comuns:

```text
iss       = conversational-ai-platform
sub       = serviço chamador
aud       = serviço destino
tenant_id = UUID canônico
iat/exp   = validade curta
jti       = identificador do token
kid       = serviço emissor
alg       = HS256
```

Cada receptor:

1. resolve a chave apenas para callers allowlisted;
2. valida assinatura, issuer, audience, algoritmo e expiração;
3. exige `kid == sub`;
4. compara `tenant_id` com `X-Tenant-Id`;
5. aplica allowlist específica do endpoint/bounded context.

O body pode repetir tenant para compatibilidade, mas não é fonte de autoridade.

### Limitação de identidade

HS256 por par reduz o raio de impacto, mas continua simétrico. Produção deve migrar para workload identity/OAuth2, JWT assimétrico com JWKS/rotação e/ou mTLS/service mesh.

## 4. Tools e policy

### Renegociação

O Agent Runtime emite `tool_execution` com:

- conversa e mensagem;
- estágio e versão da jornada;
- evidência de confirmação, quando aplicável.

O Tool Service autoriza deterministicamente a operação e emite `governed_tool`. O Renegotiation Service revalida:

- caller;
- tool assinada correspondente ao endpoint;
- estágio permitido;
- `policy_id == Idempotency-Key`;
- evidência de confirmação ligada à mensagem atual.

Prompt ou tool call do LLM não autorizam uma operação financeira por si só.

### Cartão

A skill de cartão é somente leitura. O Tool Service valida que o caller é `agent-runtime-fatura-cartao`; o Core valida que o caller final é `tool-service-cartao-credito`. Não há policy por estágio nem `Idempotency-Key`, pois os endpoints de limite/fatura não criam efeito financeiro.

## 5. Core Bancário Mock

No ambiente integrado, o Core habilita auth fail-closed e aceita:

- `renegotiation-service` nas APIs de cliente, elegibilidade, contratação e formalização;
- `tool-service-cartao-credito` apenas na Card API.

O Core disponibiliza `/health/live`, `/health/ready` e `/metrics`. A readiness retorna `503` quando auth está habilitada e algum segredo obrigatório está ausente ou inválido.

O Core não recebe o token `governed_tool` original. A autorização de jornada já foi revalidada pelo Renegotiation Service; o último hop usa identidade de serviço, tenant e idempotência.

## 6. Multitenancy

O tenant é UUID não vazio em formato canônico.

- Redis: chaves prefixadas por tenant;
- MongoDB: queries e unicidade incluem tenant;
- OpenSearch: índice físico inclui tenant canônico;
- PostgreSQL: Inbox, estado, Outbox, idempotência, Audit e Handoff incluem tenant;
- Core: scope idempotente em memória inclui tenant, operação e chave.

## 7. Integridade e durabilidade

### Entrada

- o BFF só confirma o webhook após publicação Kafka;
- o consumer usa commit manual;
- retry/DLQ precisam ser confirmados antes do commit original;
- poison messages têm limite de tentativas.

### Estado e efeitos

O Orchestrator conclui o Inbox na mesma transação que atualiza a versão da conversa e registra os efeitos na Outbox. Falha posterior mantém obrigação retryable.

### Idempotência

| Camada | Persistência | Garantia |
|---|---|---|
| BFF outbound | Redis | mesma resposta por tenant/chave |
| Memory | MongoDB | `(tenantId, externalMessageId)` |
| Audit/Handoff | PostgreSQL | `(tenant_id, idempotency_key)` |
| Renegotiation Service | PostgreSQL | hash/request/resposta duráveis |
| Core mock | memória do processo | replay/conflict para simulação e confirmação |

O Core rejeita operação mutável sem `Idempotency-Key`, replaya o mesmo request e devolve `409` para payload divergente ou execução concorrente. O store process-local não substitui a persistência durável do Renegotiation Service nem um core real.

## 8. Ordenação

- uma mensagem por conversa mantém lease ativo;
- atualização exige versão esperada;
- mensagens antigas são classificadas como `late_message`;
- efeitos carregam `journey_version`;
- versões posteriores aguardam efeitos anteriores.

## 9. PII e logging

Implementado:

- eventos `tool.executed` não incluem argumentos;
- métricas não usam CPF, conteúdo, tenant ou conversation ID como label;
- reason de handoff é normalizado;
- logs operacionais priorizam identificadores e trace.

Ainda necessário:

- redaction centralizada;
- catálogo/classificação de campos e DLP;
- retenção e descarte aprovados;
- fluxo LGPD de acesso, correção, anonimização e exclusão;
- criptografia em repouso gerenciada.

Consulte [Retenção, classificação e LGPD](../governance/data-retention-lgpd.md).

## 10. Segredos e infraestrutura

O Compose falha quando um segredo por par não é informado. Valores reais não são versionados.

Ainda faltam para produção:

- cofre de segredos e rotação/revogação;
- workload identity/JWKS/mTLS;
- Kafka TLS/SASL/ACL;
- segurança e backup gerenciado do OpenSearch;
- NetworkPolicy/service mesh;
- WAF/rate limiting;
- imagens assinadas e enforcement por digest/atestado.

## 11. Supply chain

Este repositório executa Trivy, publica SARIF e gera SBOM SPDX como artifact. O Core possui CI com testes de integração. Os controles ainda precisam ser uniformizados nos demais repositórios, incluindo:

- scan da imagem construída;
- SBOM por imagem;
- assinatura Cosign;
- GitHub artifact attestations/proveniência;
- bloqueio de deploy sem assinatura/atestado.

## 12. Observabilidade de segurança

Prometheus carrega regras versionadas e envia para Alertmanager. O baseline cobre:

- target crítico indisponível;
- DLQ;
- falha de processamento/Outbox;
- mensagens atrasadas;
- falhas de autenticação;
- negação de policy.

O receiver local é nulo. Produção precisa de integração real com incidentes, ownership, escalonamento e teste de entrega.

## 13. Lacunas críticas restantes

1. **Identidade:** HS256 por par, sem rotação/JWKS/workload identity.
2. **Core:** idempotência em memória; um core real precisa de persistência e controles próprios.
3. **Handoff:** sem plataforma humana real.
4. **Infraestrutura:** Kafka/OpenSearch/rede locais sem controles de produção.
5. **Supply chain:** assinatura/atestado e enforcement ainda não uniformes nos serviços.
6. **LGPD:** política e implementação corporativas ainda incompletas.
7. **DR:** restore local cobre PostgreSQL/MongoDB; Kafka/OpenSearch continuam reconstruíveis/replay.
8. **Evidência:** workflow E2E existe, mas depende de `MULTIREPO_READ_TOKEN` e execução registrada antes da promoção.

## 14. Classificação

O estado é uma **POC endurecida com consistência transacional, identidade por par, enforcement determinístico de tools, Core autenticado em homologação e controles operacionais executáveis**. Ainda não é production-ready bancário.
