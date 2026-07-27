# Mapa de domínios de negócio

## Objetivo

Separar a plataforma conversacional, os domínios de negócio e os sistemas corporativos. A fonte executável é [`contracts/functional/domains.yaml`](../../contracts/functional/domains.yaml).

## Domínios

| Domínio | Tipo | Responsabilidade |
|---|---|---|
| Plataforma Conversacional | Genérico | Canal, sessão, roteamento, estado opaco, memória e efeitos |
| Identidade do Cliente | Supporting | Identificação, assurance, consentimento e step-up |
| Recuperação de Crédito | Core | Contratos, elegibilidade, propostas e formalização |
| Serviços de Cartão | Core | Consultas e futuras operações de cartão |
| Gestão do Conhecimento | Supporting | Conteúdo, busca, validade e evidência |
| Atendimento Humano | Supporting | Caso, fila, atribuição, resolução e retorno |
| Campanhas e Ativação | Supporting | Segmentação, oferta, contato e atribuição |
| Governança e Evidências | Genérico | Auditoria, retenção, políticas e risco |
| Desempenho e Analytics | Supporting | Funis, qualidade, conversão e custos |
| Sistemas Bancários | Externo | Fonte transacional e registro financeiro |

## Bounded contexts

### Plataforma Conversacional

Não deve conhecer campos específicos de renegociação ou cartão. Mantém `skill_id`, `journey_stage` e `structured_state` opacos, além das garantias de Inbox/Outbox, ordenação e sessão.

### Recuperação de Crédito

É dona das regras de elegibilidade, simulação, aceite e formalização. O Agent Runtime interpreta a conversa; as regras financeiras permanecem determinísticas nos serviços de domínio e no Core.

### Serviços de Cartão

É um contexto separado de renegociação. A skill atual é somente leitura e não deve receber permissões transacionais por reutilização acidental.

### Identidade

Deve evoluir para um contexto reutilizável. O CPF não é o estado de autenticação; é um identificador usado em um processo de verificação.

## Relações principais

```text
Campanhas → Plataforma Conversacional → Identidade
                                  ├── Recuperação → Sistemas Bancários
                                  ├── Cartão → Sistemas Bancários
                                  ├── Conhecimento
                                  ├── Atendimento Humano
                                  └── Governança → Analytics
```

## Princípios de dependência

- domínios core não dependem da implementação de canal;
- agentes não são fonte de verdade financeira;
- plataforma não interpreta o estado interno das skills;
- governança recebe evidências, mas não decide regras financeiras;
- analytics consome eventos de negócio, não consulta bancos operacionais diretamente.
