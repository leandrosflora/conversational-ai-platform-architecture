# Mapa de domínios de negócio

## Objetivo

Separar a plataforma conversacional, os domínios de negócio e os sistemas corporativos. A fonte executável é `contracts/functional/domains.yaml`.

!!! warning "Implementação funcional versus fonte de dados"
    Os domínios de **Recuperação de Crédito** e **Serviços de Cartão** estão funcionalmente representados e exercitados ponta a ponta, mas usam dados sintéticos e APIs do `core-bancario-mock`. Isso comprova o desenho da jornada e os controles de integração, não a aderência a produtos, saldos, contratos ou regras financeiras reais. Na arquitetura-alvo, esses domínios devem consumir APIs reais do Core Bancário e dos sistemas de produto responsáveis.

## Domínios

| Domínio | Tipo | Responsabilidade | Implementação atual |
|---|---|---|---|
| Plataforma Conversacional | Genérico | Canal, sessão, roteamento, estado opaco, memória e efeitos | Implementada |
| Identidade do Cliente | Supporting | Identificação, assurance, consentimento e step-up | Parcial |
| Recuperação de Crédito | Core | Contratos, elegibilidade, propostas e formalização | Jornada implementada com dados mockados |
| Serviços de Cartão | Core | Consultas e futuras operações de cartão | Consulta implementada com dados mockados |
| Gestão do Conhecimento | Supporting | Conteúdo, busca, validade e evidência | Parcial |
| Atendimento Humano | Supporting | Caso, fila, atribuição, resolução e retorno | Solicitação persistida; ciclo completo é alvo |
| Campanhas e Ativação | Supporting | Segmentação, oferta, contato e atribuição | Alvo |
| Governança e Evidências | Genérico | Auditoria, retenção, políticas e risco | Baseline implementado |
| Desempenho e Analytics | Supporting | Funis, qualidade, conversão e custos | Parcial |
| Sistemas Bancários | Externo | Fonte transacional e registro financeiro | Simulados pelo Core mock; APIs reais são alvo |

## Bounded contexts

### Plataforma Conversacional

Não deve conhecer campos específicos de renegociação ou cartão. Mantém `skill_id`, `journey_stage` e `structured_state` opacos, além das garantias de Inbox/Outbox, ordenação e sessão.

### Recuperação de Crédito

É dona das regras de elegibilidade, simulação, aceite e formalização. O Agent Runtime interpreta a conversa; as regras financeiras permanecem determinísticas nos serviços de domínio e no Core.

Na referência atual, essas regras e valores são simplificados e executados sobre massas sintéticas. Em produção, elegibilidade, composição da dívida, cálculo de proposta, persistência do acordo e geração documental devem ser delegados aos sistemas bancários autorizados.

### Serviços de Cartão

É um contexto separado de renegociação. A skill atual é somente leitura e não deve receber permissões transacionais por reutilização acidental.

Os limites, valores de fatura e vencimentos atuais são sintéticos. A arquitetura-alvo deve consultar APIs reais do domínio de cartões, mantendo o Tool Service apenas como camada governada de acesso, nunca como fonte de verdade.

### Identidade

Deve evoluir para um contexto reutilizável. O CPF não é o estado de autenticação; é um identificador usado em um processo de verificação.

### Sistemas Bancários

O `core-bancario-mock` representa temporariamente este domínio externo para permitir E2E determinístico. Ele não deve ser promovido como componente produtivo. A substituição por APIs reais precisa considerar:

- contratos e versionamento de API;
- autenticação e autorização por workload;
- segregação por produto e operação;
- idempotência persistente;
- consistência e concorrência;
- regras financeiras corporativas;
- auditoria regulatória;
- SLA, timeout, retry e circuit breaker;
- mascaramento e classificação de dados;
- homologação com massas não produtivas antes da entrada em produção.

## Relações principais

```text
Campanhas → Plataforma Conversacional → Identidade
                                  ├── Recuperação → APIs reais de Sistemas Bancários
                                  ├── Cartão → APIs reais do domínio de cartões
                                  ├── Conhecimento
                                  ├── Atendimento Humano
                                  └── Governança → Analytics
```

No ambiente de referência, as duas relações com sistemas bancários terminam no `core-bancario-mock`.

## Princípios de dependência

- domínios core não dependem da implementação de canal;
- agentes não são fonte de verdade financeira;
- dados produzidos pelo mock nunca devem ser apresentados como dados bancários reais;
- plataforma não interpreta o estado interno das skills;
- governança recebe evidências, mas não decide regras financeiras;
- analytics consome eventos de negócio, não consulta bancos operacionais diretamente;
- a troca do mock por APIs reais deve preservar os contratos funcionais e reforçar os controles não funcionais.