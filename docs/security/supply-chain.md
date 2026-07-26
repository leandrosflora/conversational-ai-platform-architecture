# Supply chain, SBOM e atestações

## Controles implementados

### Repositório de arquitetura

O workflow `Attested documentation release`:

1. executa `mkdocs build --strict`;
2. empacota o site estático;
3. gera checksum SHA-256;
4. gera SBOM SPDX JSON do conteúdo construído;
5. cria atestado de proveniência;
6. cria atestado assinado da SBOM;
7. publica o bundle como artifact por 90 dias.

Ele é executado manualmente ou em tags `v*`.

### Core Bancário Mock

O workflow `Attested container release`:

1. executa a suíte de testes;
2. constrói a imagem Docker;
3. exporta a imagem em arquivo compactado;
4. gera checksum SHA-256;
5. gera SBOM SPDX JSON da imagem;
6. cria atestados de proveniência e SBOM;
7. publica o bundle de release.

## Permissões

Os workflows usam permissões mínimas explícitas:

```yaml
permissions:
  contents: read
  id-token: write
  attestations: write
  artifact-metadata: write
```

O token OIDC é usado somente durante a execução para obter a assinatura do atestado. Não existe chave privada persistente no repositório.

## Verificação

Baixe o artifact e valide o checksum:

```bash
sha256sum -c SHA256SUMS
```

Valide o atestado associado ao artefato:

```bash
gh attestation verify <arquivo> \
  --repo leandrosflora/conversational-ai-platform-architecture
```

Para o Core:

```bash
gh attestation verify core-bancario-mock-image.tar.gz \
  --repo leandrosflora/core-bancario-mock
```

A verificação deve ser feita sobre o arquivo original, sem recompressão ou alteração.

## Limitações

- apenas arquitetura e Core possuem release atestada neste change set;
- os demais serviços ainda precisam de imagem por digest, SBOM e atestação equivalentes;
- não há admission controller bloqueando artefatos sem atestado;
- o artifact compactado do Core não substitui publicação em registry corporativo;
- produção deve aplicar política de retenção, revogação e enforcement no ambiente de deploy.
