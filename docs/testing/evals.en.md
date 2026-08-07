# AI Evals

## Objective

Evals detect regressions in intent, handoff, scope, and security when the model, prompt, tool, or policy changes. They complement unit and E2E tests; they do not replace human evaluation or production metrics.

## Versioned suite

`evals/scenarios.yaml` contains deterministic scenarios for the renegotiation and card skills:

- greeting;
- renegotiation request;
- debt inquiry;
- limit and invoice inquiry;
- human-support request;
- out-of-scope message;
- attempt to instruct the agent to ignore rules.

Each scenario defines the expected intent, handoff behavior, reason, and forbidden intents. Current thresholds require a 100% pass rate, maximum online latency of 1,500 ms in mock mode, and handoff in no more than 30% of the suite.

## Offline mode

Reproduces the current deterministic mock-agent logic without starting infrastructure:

```bash
python -m pip install pyyaml
python scripts/run-evals.py \
  --mode offline \
  --output artifacts/evals-offline.json
```

This mode runs on every PR in the P8 package and detects unintended changes to the suite contract.

## Online mode

Calls both running Agent Runtimes using internal JWT and signed tenant context:

```bash
scripts/write-ci-env.sh
set -a; source .env; set +a
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
python scripts/run-evals.py \
  --mode online \
  --output artifacts/evals-online.json
```

The multi-repository workflow runs this mode after resolving every service to an exact SHA.

## Evidence

The JSON report records:

- scenario and runtime;
- pass/fail result;
- latency;
- observed response;
- expectation errors;
- pass rate;
- handoff rate;
- threshold violations.

No real customer messages are used. The suite contains only versioned synthetic datasets.

## Evolution for real models

When `MOCK_AGENT_ENABLED=false`, add datasets separated by model/prompt and measure:

- intent accuracy;
- correct tool selection;
- journey-state adherence;
- prompt-injection resistance;
- RAG groundedness;
- response quality;
- cost and tokens;
- latency;
- fallback and handoff rates.

A model, prompt, or tool change should publish a comparative report against the baseline and justify any accepted regression.
