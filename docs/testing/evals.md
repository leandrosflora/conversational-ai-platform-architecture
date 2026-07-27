# Evals de IA

## Objetivo

Os evals detectam regressões em intenção, handoff, escopo e segurança quando modelo, prompt, tool ou policy mudam. Eles complementam testes unitários e E2E; não substituem avaliação humana nem métricas de produção.

## Suite versionada

`evals/scenarios.yaml` contém cenários determinísticos para as skills de renegociação e cartão:

- saudação;
- pedido de renegociação;
- consulta de dívida;
- consulta de limite e fatura;
- pedido de atendimento humano;
- mensagem fora de escopo;
- tentativa de instrução para ignorar regras.

Cada cenário define intent esperado, handoff, motivo e intents proibidas. Os thresholds atuais exigem 100% de aprovação, latência online máxima de 1.500 ms no modo mock e handoff em no máximo 30% da suite.

## Modo offline

Reproduz a lógica determinística atual dos mock agents sem subir infraestrutura:

```bash
python -m pip install pyyaml
python scripts/run-evals.py \
  --mode offline \
  --output artifacts/evals-offline.json
```

Esse modo roda em todo PR do pacote P8 e detecta alterações involuntárias no contrato da suite.

## Modo online

Chama os dois Agent Runtimes em execução, usando JWT interno e tenant assinado:

```bash
scripts/write-ci-env.sh
set -a; source .env; set +a
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
python scripts/run-evals.py \
  --mode online \
  --output artifacts/evals-online.json
```

O workflow multi-repositório executa esse modo depois de resolver todos os serviços para SHAs exatos.

## Evidência

O relatório JSON registra:

- cenário e runtime;
- resultado aprovado/reprovado;
- latência;
- resposta observada;
- erros de expectativa;
- taxa de aprovação;
- taxa de handoff;
- violações de threshold.

Nenhuma mensagem real de cliente é usada. A suite contém somente massas sintéticas versionadas.

## Evolução para modelos reais

Quando `MOCK_AGENT_ENABLED=false`, adicionar datasets separados por modelo/prompt e medir:

- precisão de intenção;
- seleção correta de tool;
- aderência ao estado da jornada;
- resistência a prompt injection;
- groundedness de RAG;
- qualidade da resposta;
- custo e tokens;
- latência;
- taxa de fallback e handoff.

Mudança de modelo, prompt ou tool deve publicar um relatório comparativo com baseline e justificar qualquer regressão aceita.
