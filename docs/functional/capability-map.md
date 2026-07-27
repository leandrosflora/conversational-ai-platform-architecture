# Mapa de capacidades funcionais

## Objetivo

Organizar a plataforma pelo valor entregue ao negócio, independentemente dos agentes, serviços ou tecnologias usados na implementação.

A fonte executável deste mapa é `contracts/functional/capabilities.yaml`.

## Mapa L1

| Capacidade | Resultado esperado | Estado atual |
|---|---|---|
| Engajamento e canais | Atendimento 24x7 e continuidade de canal | Implementado para WhatsApp; omnichannel é alvo |
| Identidade e contexto do cliente | Acesso seguro a informações e operações | Identificação implementada; assurance e consentimento são parciais |
| Conversação e gestão de jornada | Roteamento, sessão e progressão consistente | Implementado |
| Recuperação e renegociação | Consulta, simulação, aceite e formalização | Implementado em ambiente de referência |
| Atendimento de cartão | Consulta de limite, fatura e vencimento | Implementado como skill somente leitura |
| Conhecimento corporativo | Respostas baseadas em conteúdo aprovado | Busca implementada; governança editorial é parcial |
| Atendimento humano | Continuidade para exceções | Solicitação persistida; roteamento e resolução são alvo |
| Campanhas e ativação | Oferta rastreável e atribuição de conversão | Arquitetura-alvo |
| Governança e conformidade | Auditoria, privacidade e risco de IA | Baseline implementado |
| Gestão de desempenho e valor | Conversão, qualidade, contenção e custo | Métricas técnicas parciais; funil funcional é alvo |

## Relação entre estratégia e implementação

```text
Objetivo de negócio
        ↓
Capacidade funcional
        ↓
Domínio
        ↓
Jornada / Skill
        ↓
Serviço
        ↓
API, evento e dado
```

## Regras

1. Uma capacidade existe mesmo que sua implementação tecnológica mude.
2. Skills implementam capacidades; não são capacidades por si só.
3. Serviços podem suportar várias capacidades, mas devem possuir responsabilidade principal explícita.
4. Capacidades `target` não devem ser apresentadas como disponíveis.
5. Toda capacidade implementada deve possuir owner, indicador e evidência operacional.

## Próximos gaps funcionais

- assurance e step-up independentes das skills;
- continuidade omnichannel;
- acompanhamento de acordo e pagamento;
- roteamento e resolução humana;
- curadoria e vigência do conhecimento;
- campanha e atribuição;
- funil de negócio e custos por jornada.
