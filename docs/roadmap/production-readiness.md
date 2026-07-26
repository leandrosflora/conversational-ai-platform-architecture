# Roadmap de produção e governança

## Estado

A solução é uma referência executável e uma POC endurecida. Este change set entrega baselines de operação, evidência e segurança; produção bancária continua dependendo da plataforma de execução e dos controles corporativos.

## Baselines concluídos neste change set

- Core mock com JWT/tenant por caller no Compose integrado;
- health, métricas e testes de integração do Core;
- replay/conflict idempotente process-local no Core;
- workflow E2E multi-repositório com commits e artifacts;
- regras Prometheus e Alertmanager local;
- scripts protegidos de backup/restore e chaos drill;
- baseline k6;
- documentação de SLO, DR, LGPD e supply chain;
- SBOM do repositório de arquitetura como artifact.

## P0 — bloqueadores restantes

- executar e tornar obrigatório o E2E multi-repositório antes de releases;
- provisionar receivers reais, ownership e plantão;
- substituir HS256 por workload identity/JWKS e/ou mTLS;
- implementar retenção, anonimização e exclusão aprovadas por LGPD/Jurídico;
- provar restore periódico em ambiente descartável;
- substituir idempotência process-local do mock por garantias do sistema bancário real.

## P1 — supply chain

- gerar SBOM por imagem de serviço;
- publicar imagens por digest;
- assinar imagens com Cosign;
- gerar atestados de proveniência;
- bloquear deploy sem assinatura/atestado;
- uniformizar Trivy/SAST/SCA nos 12 serviços;
- relacionar cada evidência E2E a imagens/digests exatos.

## P2 — escala e resiliência

- carga por jornada e tenant, não apenas readiness;
- chaos drills automatizados em ambiente descartável;
- budgets de custo e tokens;
- consumer lag e capacity planning Kafka;
- isolamento por workload e NetworkPolicy;
- SLOs aprovados e error budgets;
- recuperação regional e continuidade.

## Critério de encerramento

Um item só é concluído quando possui:

1. implementação;
2. teste automatizado;
3. evidência;
4. rollback;
5. owner;
6. monitoramento;
7. documentação atualizada.
