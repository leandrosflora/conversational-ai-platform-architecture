# Governança funcional do conhecimento

## Estado atual

O Knowledge Service ingere PDFs por tenant, gera chunks, embeddings e índices vetoriais. Há hash e arquivo-fonte, mas ainda falta ciclo editorial completo.

## Metadados obrigatórios alvo

```yaml
knowledgeAsset:
  id: policy-renegotiation-2026
  version: 3.1
  title: Política de renegociação
  domain: debt-recovery
  owner: Debt Recovery
  approvedBy:
    - Legal
    - Compliance
  effectiveFrom: 2026-07-01
  expiresAt: 2027-06-30
  status: published
  allowedSkills:
    - renegotiation
  allowedAudiences:
    - customer
    - human-agent
  classification: approved-for-customer
  sourceSystem: corporate-knowledge
```

## Ciclo de vida

```text
Draft → Review → Approved → Published → Superseded / Expired / Withdrawn
```

## Regras

1. Apenas conteúdo `Published` e vigente pode responder ao cliente.
2. ACL deve ser aplicada por documento e skill.
3. Toda resposta RAG deve registrar `assetId`, versão e chunks usados.
4. Conteúdo expirado é excluído da busca antes da remoção física.
5. Alteração de política exige reindexação rastreável.
6. Resultado sem evidência suficiente deve gerar fallback, não resposta inventada.
7. Dados de tenant não podem usar fallback para conteúdo de outro tenant em produção.

## Indicadores

- cobertura de conteúdo aprovado;
- groundedness;
- taxa de busca sem resultado;
- ativos expirados ainda indexados;
- tempo entre aprovação e publicação;
- respostas contestadas por owner.
