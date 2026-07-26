# whatsapp-bff

Repo: [`leandrosflora/whatsapp-bff`](https://github.com/leandrosflora/whatsapp-bff) · Stack: .NET 8, Minimal API, Confluent.Kafka · Porta local: `5153`

## Responsabilidade principal

Channel BFF entre o WhatsApp Cloud API e o `conversation-orchestrator`. Recebe e valida os webhooks do WhatsApp, persiste a entrega bruta no Kafka antes de confirmar recebimento (garantindo que uma queda do processo não perca mensagens já aceitas), encaminha mensagens de forma assíncrona para o Orchestrator com retry-until-success, e expõe um endpoint interno para enviar respostas de volta ao cliente pela Graph API.

Funções principais:
- Verificar o webhook configurado na Meta (`GET /webhooks/whatsapp`).
- Validar a assinatura HMAC-SHA256 (`X-Hub-Signature-256`) de cada entrega.
- Deduplicar entregas repetidas por `message.id`.
- Publicar o payload bruto no Kafka antes de confirmar o recebimento à Meta.
- Consumir esse mesmo tópico e encaminhar as mensagens ao Orchestrator.
- Publicar eventos canônicos de mensagem recebida/status.
- Enviar mensagens de saída pela WhatsApp Cloud API.

## Dados que o serviço possui

Modelos de domínio (`Domain/`): `InboundChannelMessage`, `MessageStatusEvent` (+ `StatusError`), `OutboundChannelMessage`, `InteractiveReply`, `ChannelMessageType` (enum `Text=0, Interactive=1, Unsupported=2` — ordem fixa por compatibilidade de serialização com o `conversation-orchestrator`), `MessageDeliveryStatus`. Nenhum desses modelos é persistido em banco — vivem durante o processamento de uma requisição/mensagem Kafka. Há, no entanto, um estado real persistido: uma reserva de idempotência outbound no Redis (`IOutboundDeliveryStore`, chaveada por `tenantId` + `Idempotency-Key`), usada por `POST /internal/messages`.

## APIs publicadas

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/webhooks/whatsapp` | Handshake de verificação do webhook (`hub.mode`, `hub.verify_token`, `hub.challenge`) |
| `POST` | `/webhooks/whatsapp` | Recebe entregas do WhatsApp Cloud API (mensagens e eventos de status) |
| `POST` | `/internal/messages` | Endpoint interno (JWT + `X-Tenant-Id`) usado pelo Orchestrator para enviar uma resposta ao cliente |

`POST /webhooks/whatsapp` retorna `200 OK` (aceito ou duplicado descartado), `400 Bad Request` (payload inválido), `401 Unauthorized` (assinatura ausente/inválida) ou `503 Service Unavailable` (falha ao persistir no Kafka — sinaliza a Meta para reentregar).

`POST /internal/messages` exige `Authorization: Bearer <JWT>` (`401` se ausente/inválido), `X-Tenant-Id` batendo com a claim `tenant_id` assinada (`403` caso contrário) e um header `Idempotency-Key` (`400` se ausente). Com uma chave de idempotência nova, executa o envio; se a chave já foi concluída antes, responde `202 Accepted` com `{"messageId", "duplicate": true}` sem reenviar; se a chave está com um envio em andamento/ambíguo, responde `409 Conflict` (`reconciliationRequired: true`). Outras respostas: `400 Bad Request` (`to`/`text` ausentes; `buttons` ausente/vazio ou com mais de 3 itens para `type=interactive`) e `502 Bad Gateway` (falha ambígua na WhatsApp Cloud API — a reserva Redis **não** é liberada nesse caso, para não permitir um reenvio automático duplicado; requer reconciliação manual).

## Eventos publicados

| Tópico | Quando | Payload | Falha é engolida? |
|---|---|---|---|
| `channel.webhook.received` | Sempre, antes de responder ao webhook (síncrono dentro do request) | JSON bruto da entrega; chave = telefone do remetente; header `CorrelationId` | **Não** — falha vira `503`, propositalmente |
| `channel.message.received` | Após o forward ao Orchestrator ter sucesso | `InboundChannelMessage` | Sim (catch-log-continue) |
| `channel.message.status` | Para cada evento de status recebido do WhatsApp | `MessageStatusEvent` (com `IsKnownMessage`) | Sim (catch-log-continue) |
| `channel.webhook.received.retry` | Quando o processamento de uma entrega falha (JSON inválido, `Orchestrator` rejeitou, exceção) e ainda não esgotou `MaxDeliveryAttempts` (padrão 5) | Mesmo payload bruto, com header `x-delivery-attempt` incrementado e `retry-reason` | Se o próprio publish falhar, o consumer faz `Seek` de volta ao offset original em vez de perder a entrega |
| `channel.webhook.received.dlq` | Quando a entrega é poison (JSON inválido/payload nulo) ou esgotou as tentativas de retry | Payload bruto + `x-delivery-attempt`, `dead-letter-reason`, tópico/partição/offset de origem | Mesmo comportamento de replay-on-failure do publish acima |

## Eventos consumidos

`channel.webhook.received` **e** `channel.webhook.received.retry` — ambos consumidos pelo próprio processo via `KafkaWebhookConsumerService` (mesmo consumer group), não por outro serviço.

## Dependências síncronas

| Destino | Chamada | Comportamento se indisponível |
|---|---|---|
| `conversation-orchestrator` (`:8000` dev local / `:5268` via `docker compose`) | `POST /messages` | `AddStandardResilienceHandler`: até 2 tentativas extras, `AttemptTimeout=30s`, `TotalRequestTimeout=35s`. Se a entrega inteira falhar (todas as tentativas HTTP esgotadas, ou o Orchestrator recusar), o consumer republica em `channel.webhook.received.retry` com backoff fixo de `RetryBackoffSeconds` (padrão 2s) até `MaxDeliveryAttempts` (padrão 5), depois manda para a DLQ — nunca faz `Seek`/replay infinito no mesmo offset, exceto como fallback se o próprio publish de retry/DLQ falhar |
| WhatsApp Cloud API (Graph API) | `POST /{phone-number-id}/messages` | Falha vira `502 Bad Gateway` no `POST /internal/messages` — **sempre** o caso em ambiente local/demo sem uma WhatsApp Business Account real configurada, não só quando o Graph API está fora do ar |

> A validação de 2026-07-13 ([relatório](../validation/2026-07-13-e2e-journey.md)) havia observado a mesma mensagem inbound sendo processada duas vezes pelo Agent Runtime quando o Orchestrator excedia o timeout então vigente (10s) — o Orchestrator não deduplicava por `MessageId`. O Orchestrator hoje mantém um Inbox transacional no PostgreSQL com chave `(tenant_id, message_id)` (`ops.message_inbox`, ver [conversation-orchestrator](conversation-orchestrator.md)), que resolve exatamente esse cenário: uma segunda entrega do mesmo `messageId` encontra a linha já `completed` (ou com lease `processing` ainda válido) e não reprocessa. O timeout do lado do `whatsapp-bff` também subiu para `AttemptTimeout=30s`/`TotalRequestTimeout=35s`.

## Persistência & infraestrutura

- **Kafka**: fila durável de entrada (`channel.webhook.received` + `.retry` + `.dlq`) e saída de eventos canônicos.
- **Redis**: reserva de idempotência para `POST /internal/messages` (`IOutboundDeliveryStore`), chaveada por tenant + `Idempotency-Key`.
- **Deduplicação de entregas de webhook**: em memória (`IMessageDedupeStore`), perdida em restart.
- **Rastreamento de mensagens outbound conhecidas**: em memória, também perdido em restart.
- Sem banco de dados relacional/documento.

## Regras de negócio

1. O webhook só é confirmado (`200 OK`) à Meta depois que o payload bruto foi duravelmente publicado no Kafka — nunca antes.
2. O consumer Kafka só avança (commita) o offset depois de a entrega ser processada com sucesso **ou** de o retry/DLQ correspondente ter sido publicado com sucesso; se nem o processamento nem a publicação de retry/DLQ funcionarem, o consumer faz `Seek` de volta ao offset original em vez de perder a entrega.
3. Uma entrega poison (JSON inválido ou payload nulo) vai direto para a DLQ, sem passar por retry — reprocessar os mesmos bytes nunca teria sucesso.
4. Uma entrega que falha por outro motivo (Orchestrator recusou, exceção durante o processamento) é republicada em `channel.webhook.received.retry` com backoff fixo até esgotar `MaxDeliveryAttempts` (padrão 5), e só então vai para a DLQ.
5. Deduplicação de webhook: uma entrega só é considerada duplicada se **todos** os `message.id` nela já tiverem sido processados antes.
6. `POST /internal/messages` é idempotente por `Idempotency-Key`: uma chave já concluída retorna o mesmo `messageId` sem reenviar; uma chave em andamento/ambígua retorna `409` em vez de arriscar um envio duplicado.
7. Imediatamente após persistir a entrega no Kafka, o serviço tenta (best-effort, nunca lança) mostrar o indicador "digitando..." ao cliente via `POST /{phone-number-id}/messages` (`mark_as_read` + `typing_indicator`), antes mesmo do Orchestrator/Agent Runtime responderem.

## Referências de arquitetura

- [ADR 0001 — Kafka como fila durável de entrada de webhook](../adr/0001-kafka-durable-webhook-queue.md)
- [ADR 0004 — Resiliência catch-log-continue](../adr/0004-catch-log-continue-resilience.md)
- [Diagramas de sequência da jornada](../architecture/sequence-diagrams.md)
