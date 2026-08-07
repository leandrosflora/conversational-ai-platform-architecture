# Functional KPI Map

## Objective

Connect business objectives to events and journeys. The executable source is `contracts/functional/kpis.yaml`.

## Main KPIs

| Dimension | Indicators |
|---|---|
| Recovery | completion, acceptance, conversion, recovered value, time to agreement |
| Card | inquiry success |
| Service | digital containment, handoff, resolution time |
| Quality | out-of-scope rate, groundedness |
| Efficiency | AI cost per completed journey |

## Renegotiation funnel

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

## Measurement rules

1. Denominators use unique journeys, not message counts.
2. Reprocessing is deduplicated by event.
3. Monetary metrics record currency and reference date.
4. Conversion must be segmentable by tenant, campaign, product, and channel.
5. Handoff must be analyzed by reason.
6. Targets are approved only after a baseline is established at representative volume.
7. AI indicators do not replace financial and experience outcomes.

## Current gaps

- `PaymentConfirmed` is still a target capability;
- there is no end-to-end `campaignId` yet;
- cost and tokens are not linked to `journeyId`;
- groundedness still depends on evals rather than production sampling;
- handoff has no real resolution lifecycle.
