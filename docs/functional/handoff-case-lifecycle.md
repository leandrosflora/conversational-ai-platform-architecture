# Ciclo de vida do caso humano

## Estado atual

O Handoff Service persiste uma solicitação `pending`. Ainda não existe fila real, atribuição, aceite, resolução ou retorno à automação.

## Modelo-alvo

```text
Requested
   → Queued
   → Assigned
   → Accepted
   → InProgress
   → Resolved
       ├── Closed
       └── ReturnedToAutomation

Saídas alternativas: Rejected, Expired, Abandoned
```

## Dados mínimos do caso

- `caseId`, `tenantId` e `journeyId`;
- skill e estágio de origem;
- motivo e reason code;
- prioridade, fila e SLA;
- resumo gerado pela IA;
- contexto de identidade e nível de garantia;
- transcript mínimo necessário;
- dados coletados;
- tools executadas;
- propostas apresentadas;
- owner e operador;
- resultado e disposição final.

## Regras de negócio

1. O cliente não deve repetir informações já verificadas.
2. O resumo não substitui o histórico auditável.
3. PII deve obedecer minimização por fila.
4. Casos críticos podem exigir prioridade e fila específicas.
5. `ReturnedToAutomation` exige estado de retomada explícito.
6. O encerramento deve publicar `HandoffResolved`.
7. SLA começa em `Requested`, não em `Accepted`.

## Incrementos recomendados

1. corrigir identidade real da conversa, removendo a FK seed;
2. incluir `skill_id`, prioridade, fila e SLA;
3. adicionar APIs de atribuição, aceite e encerramento;
4. publicar eventos de ciclo de vida;
5. integrar plataforma de atendimento;
6. permitir retorno seguro ao bot.
