# Mapa de KPIs funcionais

## Objetivo

Conectar objetivos de negócio aos eventos e jornadas. A fonte executável está em [`contracts/functional/kpis.yaml`](../../contracts/functional/kpis.yaml).

## KPIs principais

| Dimensão | Indicadores |
|---|---|
| Recuperação | conclusão, aceite, conversão, valor recuperado, tempo até acordo |
| Cartão | sucesso de consulta |
| Atendimento | contenção digital, handoff, tempo de resolução |
| Qualidade | fora de escopo, groundedness |
| Eficiência | custo de IA por jornada concluída |

## Funil de renegociação

```text
CustomerIdentified
  → DebtPortfolioPresented
  → EligibilityAssessed
  → OfferPresented
  → OfferAccepted
  → AgreementFormalized
  → DocumentDelivered
  → PaymentConfirmed
```

## Regras de medição

1. Denominadores usam jornadas únicas, não quantidade de mensagens.
2. Reprocessamento é deduplicado por evento.
3. Métricas monetárias registram moeda e data de referência.
4. Conversão deve ser segmentável por tenant, campanha, produto e canal.
5. Handoff deve ser analisado por motivo.
6. Meta só é aprovada após baseline em volume representativo.
7. Indicadores de IA não substituem resultados financeiros e de experiência.

## Lacunas atuais

- `PaymentConfirmed` ainda é capacidade alvo;
- não existe `campaignId` ponta a ponta;
- custo e tokens não estão ligados a journeyId;
- groundedness ainda depende de eval, não de amostragem produtiva;
- handoff não possui resolução real.
