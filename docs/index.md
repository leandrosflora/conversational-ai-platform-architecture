# Conversational AI Platform Architecture

Arquitetura de referência executável para plataformas corporativas de IA conversacional com agentes, MCP, RAG, WhatsApp, sistemas transacionais, segurança interna e observabilidade ponta a ponta.

!!! warning "Dados bancários sintéticos"
    As jornadas de **renegociação** e **cartão de crédito** usam exclusivamente dados de teste, CPFs reservados e respostas geradas pelo `core-bancario-mock`. Nenhuma informação financeira real, contrato real, fatura real ou operação bancária real é processada. Na arquitetura-alvo, o mock deve ser substituído por APIs reais e governadas do Core Bancário, preservando os contratos funcionais, controles de identidade, autorização, idempotência, auditoria e observabilidade.

[:material-sitemap-outline: Explorar a arquitetura](architecture/c4-context.md){ .md-button .md-button--primary }
[:material-github: Ver o repositório](https://github.com/leandrosflora/conversational-ai-platform-architecture){ .md-button }

## Visão arquitetural

<div class="grid cards" markdown>

-   :material-check-circle-outline:{ .lg .middle } **Estado implementado**

    ---

    WhatsApp Cloud API, OpenAI, Core Bancário Mock autenticado, 12 serviços, cinco datastores e observabilidade local executável. Os domínios de renegociação e cartão operam com massas sintéticas de teste.

    [Abrir C4 de contexto atual](architecture/C4/c4-context.puml)

-   :material-office-building-cog-outline:{ .lg .middle } **Arquitetura-alvo corporativa**

    ---

    Salesforce, Data Lake, automação de campanha, atendimento humano integrado, Model Gateway, PDP, infraestrutura gerenciada e APIs reais do Core Bancário para contratos, débitos, elegibilidade, simulações, formalização, limite e fatura.

    [Abrir C4 de contexto alvo](architecture/C4/c4-context-target.puml)

</div>

## Capacidades centrais

<div class="grid cards" markdown>

-   :material-robot-outline:{ .lg .middle } **Orquestração de agentes**

    ---

    Runtime, contexto e ferramentas governadas coordenam jornadas de renegociação e cartão.

    [Agent Runtime](services/agent-runtime-renegotiation.md)

-   :material-tools:{ .lg .middle } **MCP governado**

    ---

    Tool calling com autorização determinística, caller allowlisted e contratos explícitos.

    [Tool Service MCP](services/tool-service-renegotiation.md)

-   :material-database-search-outline:{ .lg .middle } **RAG e memória**

    ---

    Conhecimento vetorial, memória de curto/longo prazo e isolamento por tenant.

    [Knowledge Service](services/knowledge-service.md)

-   :material-chart-timeline-variant:{ .lg .middle } **Observabilidade operacional**

    ---

    Alloy, Loki, Jaeger, Prometheus, Alertmanager e Grafana correlacionam sinais e regras.

    [SLOs e alertas](operations/slo-alerting.md)

-   :material-shield-check-outline:{ .lg .middle } **Segurança e consistência**

    ---

    HMAC, JWT por par, tenant assinado, Core autenticado, Inbox/Outbox e idempotência protegem a operação.

    [Arquitetura de segurança](security/security-architecture.md)

-   :material-test-tube:{ .lg .middle } **Evidência executável**

    ---

    CI, E2E multi-repositório, SBOM, backup/restore e carga/caos produzem evidências auditáveis sobre a integração e os controles, não sobre dados financeiros reais.

    [Runbook](runbook.md)

</div>

## Jornada conversacional

| Etapa | Responsabilidade |
|---|---|
| Entrada | BFF valida assinatura e garante entrada durável |
| Orquestração | Orchestrator controla Inbox, estado e Outbox |
| Raciocínio | Agent Runtime decide a próxima ação |
| Ferramentas | Tool Service aplica identidade e policy |
| Domínio | Renegotiation Service revalida e coordena o Core |
| Core | O mock fornece dados sintéticos; no alvo, APIs bancárias reais validam caller/tenant e protegem operações mutáveis |
| Suporte | memória, conhecimento, auditoria e handoff completam a experiência |

[Ver diagramas de sequência](architecture/sequence-diagrams.md){ .md-button }

## Stack e padrões

| Capacidade | Tecnologia ou padrão |
|---|---|
| Serviços | .NET, Python, arquitetura hexagonal e REST |
| Agentes | Strands, OpenAI e MCP |
| Mensageria | Kafka, Inbox/Outbox e idempotência |
| Conhecimento | OpenSearch vetorial |
| Estado | PostgreSQL, MongoDB e Redis |
| Segurança | HMAC, JWT por par, tenant assinado e tools governadas |
| Observabilidade | OpenTelemetry, Alloy, Prometheus, Alertmanager, Grafana, Loki e Jaeger |
| Supply chain | Trivy, SARIF e SBOM SPDX |
| Execução | Docker Compose, GitHub Actions, k6 e scripts de drill |

!!! success "Arquitetura executável"
    O projeto registra validações reais, smoke test de infraestrutura e um workflow E2E coordenado dos 12 serviços usando massas sintéticas e um Core Bancário mockado.