# Workload Identity, JWKS e PDP

## Estado

O profile padrão da POC continua usando HS256 com segredo independente por par de serviços. `docker-compose.security.yml` adiciona uma implementação executável e isolada da evolução alvo:

- emissor de tokens RS256;
- descoberta OIDC;
- publicação JWKS;
- credenciais curtas por workload e audience;
- allowlist de pares emissor/destino;
- decisão centralizada no OPA;
- policy com evidência obrigatória para ações financeiras.

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
| `POST /token` | token curto para par permitido |
| `POST /authorize` | valida JWT/tenant e consulta OPA |
| `GET /health/ready` | readiness incluindo OPA |

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
credencial emitida por identidade de workload
   ↓
mTLS/SPIFFE e policy corporativa
```

Durante o modo dual, o serviço deve registrar qual mecanismo validou cada chamada, sem gravar token ou conteúdo sensível.

## Controles de produção necessários

A implementação local gera uma chave RSA no primeiro startup e oferece `/token` sem autenticação de cliente. Isso é proposital para demonstração isolada e seria inseguro como emissor corporativo.

Produção precisa de:

- autenticação forte do workload solicitante;
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

`security/opa/platform_test.rego` cobre par permitido, par desconhecido, divergência de tenant e evidência financeira. O workflow `Security control plane` também sobe o ambiente e valida emissão RS256, JWKS e decisões reais.
