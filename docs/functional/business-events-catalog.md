# Catálogo de eventos de negócio

## Objetivo

Representar resultados funcionais, e não apenas telemetria técnica. O catálogo executável está em [`contracts/functional/business-events.yaml`](../../contracts/functional/business-events.yaml).

## Envelope mínimo

Todo evento funcional deve conter:

- `eventId`;
- `eventType`;
- `occurredAt`;
- `tenantId`;
- `journeyId`;
- `journeyVersion`;
- `skillId`;
- `correlationId`;
- `outcome`;
- `reasonCode`.

Dados pessoais devem ser tokenizados; texto livre de cliente não pertence ao envelope padrão.

## Eventos principais

| Etapa | Eventos |
|---|---|
| Identidade | `CustomerIdentified` |
| Carteira | `DebtPortfolioPresented`, `ContractSelected` |
| Elegibilidade | `EligibilityAssessed` |
| Oferta | `OfferSimulated`, `OfferPresented`, `OfferAccepted` |
| Formalização | `AgreementFormalized`, `DocumentDelivered` |
| Cartão | `CardInformationDelivered` |
| Roteamento | `SkillOutOfScope` |
| Humano | `HandoffRequested`, `HandoffAssigned`, `HandoffResolved` |
| Encerramento | `JourneyAbandoned`, `PaymentConfirmed` |

## Distinção técnica

Eventos atuais como `intent.detected` e `conversation.state_changed` continuam úteis para operação. Eles não substituem eventos de negócio, pois não comprovam que uma oferta foi apresentada, aceita ou formalizada.

## Regras

1. O produtor é o domínio que confirma o fato.
2. Eventos financeiros carregam valor e moeda quando aplicável.
3. `reasonCode` usa vocabulário controlado.
4. Eventos são imutáveis e idempotentes por `eventId`.
5. Reprocessamento não pode duplicar indicadores.
6. Eventos de capacidade alvo podem existir no catálogo antes da implementação, mas devem ser marcados no roadmap.
