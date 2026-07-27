# Workload Identity, JWKS e PDP

## Estado

O profile padrão da POC continua usando HS256 com segredo independente por par de serviços. `docker-compose.security.yml` adiciona uma implementação executável e isolada da evolução alvo:

- emissor de tokens RS256;
- descoberta OIDC;
- publicação JWKS;
- tokens curtos por workload e audience;
- autenticação bootstrap distinta por workload antes da emissão;
- allowlist de pares emissor/destino;
- decisão centralizada no OPA;
- policy com evidência obrigatória para ações financeiras;
- readiness fail-closed quando OPA ou credenciais bootstrap estão inválidos.

Esse profile demonstra a migração e os contratos. Ele não substitui um provedor corporativo de identidade.

## Execução

```bash
docker compose -f docker-compose.security.yml up -d --build --wait
python scripts/validate-security-control-plane.py
docker compose -f docker-compose.security.yml down -v
```

Endpoints locais:

| Endpoint | Finalidade |
|---|---|
| `GET /.well-known/openid-configuration` | descoberta OIDC |
| `GET /jwks.json` | chave pública RS256 |
| `POST /token` | token curto para par permitido, após bootstrap authentication |
| `POST /authorize` | valida JWT/tenant e consulta OPA |
| `GET /health/ready` | readiness incluindo OPA e configuração bootstrap |

## Emissão autenticada

O solicitante envia sua identidade no corpo e prova que possui a credencial bootstrap correspondente:

```http
POST /token
X-Workload-Bootstrap-Token: <credencial do workload>
Content-Type: application/json

{
  "client_id": "renegotiation-service",
  "audience": "core-bancario-mock",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "ttl_seconds": 120
}
```

O control plane:

1. resolve a credencial esperada pelo `client_id`;
2. compara em tempo constante;
3. verifica se o par caller/audience é permitido;
4. emite RS256 com `kid`, `sub`, `aud`, `tenant_id`, `jti` e expiração curta.

As credenciais presentes no Compose são somente placeholders locais e são distintas por workload. Produção deve injetá-las por secret manager ou eliminar o bootstrap compartilhado usando identidade nativa, SPIFFE/SPIRE ou mTLS.

## Policy centralizada

`security/opa/platform.rego` recebe:

```json
{
  "claims": {
    "sub": "renegotiation-service",
    "tenant_id": "00000000-0000-0000-0000-000000000001"
  },
  "audience": "core-bancario-mock",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "action": "confirmar_acordo",
  "resource": "/simulations/sim-1/confirmations",
  "context": {
    "policy_id": "policy-1",
    "message_id": "message-1",
    "confirmation_message_id": "message-1"
  }
}
```

A decisão permite leitura para pares autorizados, mas exige `policy_id` para simulação e evidência ligada à mensagem atual para confirmação.

## Migração recomendada

```text
HS256 por par
   ↓
dual validation HS256 + RS256
   ↓
RS256/JWKS como padrão
   ↓
credencial emitida por identidade nativa de workload
   ↓
mTLS/SPIFFE e policy corporativa
```

Durante o modo dual, o serviço deve registrar qual mecanismo validou cada chamada, sem gravar token ou conteúdo sensível.

## Controles de produção necessários

A implementação local autentica a emissão com credenciais bootstrap por workload. Isso elimina a autoafirmação de `client_id`, mas ainda não equivale a identidade nativa.

Produção ainda precisa de:

- identidade forte do workload sem segredo compartilhado;
- chave em HSM/KMS;
- rotação e revogação;
- issuer HTTPS estável;
- alta disponibilidade;
- decision logs com proteção de PII;
- bundles OPA assinados;
- política de fallback fail-closed;
- rate limiting e auditoria do endpoint de token;
- integração com IAM/OAuth2, SPIFFE/SPIRE ou identidade nativa da plataforma.

## Testes

`security/opa/platform_test.rego` cobre par permitido, par desconhecido, divergência de tenant e evidência financeira. O workflow `Security control plane` sobe o ambiente e valida:

- readiness fail-closed;
- descoberta e JWKS;
- emissão negada sem credencial;
- emissão negada com credencial incorreta;
- emissão RS256 autenticada;
- allowlist de pares;
- decisões OPA positivas e negativas;
- divergência de tenant.
