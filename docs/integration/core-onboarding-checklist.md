# Checklist de onboarding de APIs bancárias reais

## Contrato e ownership

- OpenAPI oficial e versionado;
- owner técnico e owner de negócio;
- SLA, SLO e janela de manutenção;
- política de depreciação;
- sandbox representativo.

## Segurança e dados

- workload identity e autorização por operação;
- classificação dos dados;
- criptografia e gestão de segredos;
- minimização, retenção e mascaramento;
- trilha de auditoria aprovada.

## Consistência financeira

- idempotência persistente;
- regras de concorrência;
- data de referência dos valores;
- expiração de ofertas;
- reconciliação de acordos;
- tratamento de duplicidade e replay.

## Resiliência

- timeouts e limites de consumo;
- retries apenas para erros retryable;
- circuit breaker;
- contingência e degradação;
- RTO e RPO do provider.

## Certificação

- testes de contrato consumer-driven;
- testes contra sandbox;
- cenários de resposta parcial;
- erros normalizados;
- validação de Segurança, LGPD, Jurídico e negócio;
- evidência de que a release de produção não referencia mock;
- rollback por versão de adapter e contrato.

## Go-live

A integração só pode ser promovida quando os itens obrigatórios estiverem registrados como evidência no release lock e vinculados ao digest exato do adapter certificado.
