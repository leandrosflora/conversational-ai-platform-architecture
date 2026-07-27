# Contexto funcional de identidade do cliente

## Objetivo

Separar identificação, autenticação e autorização da lógica de cada skill.

## Níveis de garantia

| Nível | Uso permitido |
|---|---|
| `anonymous` | FAQ pública e orientação geral |
| `identified` | Contexto não sensível |
| `verified` | Consulta de dados financeiros |
| `strong_authenticated` | Formalização e operações de maior risco |

## Contexto compartilhado

```yaml
identityContext:
  subjectToken: opaque-customer-token
  assuranceLevel: verified
  verifiedAt: 2026-07-27T00:00:00Z
  expiresAt: 2026-07-27T00:15:00Z
  methods:
    - cpf
    - otp
  purposes:
    - debt_renegotiation
  channelBinding: whatsapp
  evidenceId: audit-reference
```

## Regras

1. CPF não deve ser propagado como identificador primário entre serviços.
2. Skills recebem token opaco e nível de garantia.
3. Mudança para operação de maior risco pode exigir step-up.
4. Expiração do contexto não deve depender apenas da expiração da conversa.
5. Consentimento e finalidade devem ser registrados separadamente.
6. Troca de canal pode invalidar `channelBinding`.
7. Identidade deve ser reutilizada entre skills apenas dentro da finalidade e validade permitidas.

## Aplicação atual

- Renegociação e cartão exigem `verified`.
- Confirmação de acordo está catalogada como operação de step-up.
- A implementação atual baseada em CPF é um baseline, não o modelo final de identidade.
