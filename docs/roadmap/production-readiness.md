# Roadmap de produção e governança

## Estado

A solução é uma referência executável e uma POC endurecida. Os controles deste repositório melhoram repetibilidade e evidência, mas produção bancária exige implementação coordenada nos repositórios de serviço e na plataforma de execução.

## P0 — bloqueadores

- validar JWT, tenant e idempotência no `core-bancario-mock`;
- executar E2E multi-repositório em agenda e antes de releases;
- provisionar receivers reais e ownership de alertas;
- substituir segredos HS256 por workload identity/JWKS ou mTLS;
- implementar retenção, anonimização e exclusão aprovadas por LGPD/Jurídico;
- provar restore em ambiente descartável.

## P1 — supply chain

- gerar SBOM por imagem de serviço;
- publicar imagens por digest;
- assinar imagens e gerar atestados de proveniência;
- bloquear deploy de artefato sem assinatura/atestado;
- uniformizar Trivy/SAST/SCA em todos os repositórios;
- registrar versões exatas dos 12 repositórios em cada evidência E2E.

## P2 — escala e resiliência

- testes de carga por jornada e tenant;
- chaos drills automatizados;
- budgets de custo/tokens;
- consumer lag e capacidade Kafka;
- isolamento de workloads e NetworkPolicy;
- SLOs aprovados e error budgets;
- recuperação regional e testes de continuidade.

## Critério de encerramento

Um item só é concluído quando possui:

1. implementação;
2. teste automatizado;
3. evidência;
4. rollback;
5. owner;
6. monitoramento;
7. documentação atualizada.
