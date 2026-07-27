# Governança de release e contratos executáveis

## Objetivo

A plataforma é composta por este repositório de arquitetura e 12 repositórios de serviço. Uma release não é uma coleção de branches móveis: é um conjunto imutável de commits que foi construído, testado e promovido em conjunto.

## Manifesto e lock

`release/release-manifest.yaml` declara os repositórios, papéis e referências de entrada. Referências de desenvolvimento podem ser branches ou tags. Antes de qualquer build, `scripts/checkout-release.py` resolve cada referência e grava `artifacts/e2e/release-lock.yaml` com os SHAs exatos.

O lock é a unidade promovível. Uma evidência que não contenha o lock não comprova uma release multi-repositório reproduzível.

```bash
python -m pip install pyyaml
python scripts/checkout-release.py \
  release/release-manifest.yaml \
  ../workspace-release \
  --lock artifacts/e2e/release-lock.yaml
```

No GitHub Actions, o workflow `Multi-repository E2E` usa `MULTIREPO_READ_TOKEN` somente para leitura. O token não é salvo no lock nem nos artifacts.

## Contratos versionados

| Contrato | Arquivo | Garantia |
|---|---|---|
| HTTP interno | `contracts/openapi/internal-platform.yaml` | operações, headers de autenticação, tenant e idempotência |
| Kafka | `contracts/asyncapi/platform-events.yaml` | nove tópicos e envelope mínimo de evento |
| Autorização | `contracts/policy/authorization.yaml` | caller, audience, métodos, caminhos e obrigações |
| Composição | `release/release-manifest.yaml` | inventário e papéis dos 13 repositórios |

Validação local:

```bash
python scripts/validate-executable-contracts.py
```

O validador falha quando:

- um serviço ou caller não existe no manifesto;
- uma operação interna não declara JWT e tenant;
- uma mutação idempotente não declara `Idempotency-Key`;
- os tópicos AsyncAPI divergem do Kafka provisionado;
- uma regra de autorização referencia workload inexistente;
- o número de repositórios muda sem atualização coordenada.

## Processo de promoção

```text
manifesto de entrada
        ↓
resolução para SHAs
        ↓
release-lock.yaml
        ↓
build e testes por repositório
        ↓
contratos + evals + E2E
        ↓
SBOM, checksums e evidências
        ↓
promoção do mesmo lock
```

Não se deve reconstruir uma release a partir de `main`/`master` depois da homologação. A promoção deve reutilizar os mesmos SHAs e artifacts atestados.

## Critérios mínimos

Uma release é candidata somente quando possui:

1. lock com os 13 SHAs;
2. pipelines de serviço aprovados;
3. contratos executáveis aprovados;
4. E2E multi-repositório aprovado;
5. evals aprovados;
6. scan e SBOM por serviço;
7. evidência de resiliência aplicável;
8. rollback para um lock anterior conhecido.

## Limitações

O manifesto resolve código por SHA, mas o ambiente local ainda constrói imagens no momento do teste. Produção deve promover imagens por digest já atestadas, sem rebuild entre ambientes.
