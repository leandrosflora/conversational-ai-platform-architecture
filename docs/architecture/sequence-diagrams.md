# Diagramas de sequência — estado implementado

Os diagramas descrevem o change set coordenado da plataforma. A arquitetura-alvo permanece em `C4/c4-container-target.puml`.

## 1. Aceite da mensagem e operação governada

```plantuml
@startuml
hide footbox
autonumber

actor Cliente
participant "WhatsApp Cloud API" as Meta
participant "whatsapp-bff" as BFF
queue "Kafka\nchannel.webhook.received" as Kafka
participant "conversation-orchestrator" as Orch
database "PostgreSQL\nInbox + State + Outbox" as Pg
participant "agent-runtime-renegotiation" as Agent
participant "tool-service-renegotiation" as Tools
participant "renegotiation-service" as Reneg
participant "Core Bancário Mock" as Core

Cliente -> Meta: mensagem
Meta -> BFF: POST /webhooks/whatsapp\nX-Hub-Signature-256
BFF -> BFF: valida HMAC e reserva messageId
BFF ->> Kafka: payload bruto + traceparent
Kafka --> BFF: confirmação de persistência
BFF --> Meta: 200 OK

Kafka ->> BFF: entrega ao consumer
BFF -> Orch: POST /messages\nJWT + X-Tenant-Id
Orch -> Pg: acquire Inbox + lease da conversa
Pg --> Orch: checkpoint(stage, version, lastReceivedAt)

alt mensagem atrasada
  Orch -> Pg: Inbox=completed\nreason=late_message
  Orch --> BFF: 202
else mensagem atual
  Orch -> Agent: POST /process\nmessageId + stage + version
  Agent -> Tools: MCP + JWT tool_execution
  Tools -> Tools: valida caller, stage, versão\ne evidência de confirmação

  alt operação permitida
    Tools -> Reneg: JWT governed_tool\npolicy_id + Idempotency-Key
    Reneg -> Reneg: revalida tool/stage/evidência
    Reneg -> Core: JWT de serviço + tenant\nIdempotency-Key
    Core -> Core: valida caller/tenant\nreserva/replaya chave mutável
    Core --> Reneg: resposta
    Reneg --> Tools: resposta
  else policy negada
    Tools --> Agent: erro de autorização
  end

  Agent --> Orch: decisão estruturada
  Orch -> Orch: aplica máquina de estados
  Orch -> Pg: BEGIN\nUPDATE state\nINSERT Outbox\nUPDATE Inbox=completed\nCOMMIT
  Orch --> BFF: 202 Accepted
end

BFF -> Kafka: commit offset
@enduml
```

## 2. Dispatcher da Outbox

```plantuml
@startuml
hide footbox
autonumber

participant "OutboxDispatcher" as Dispatcher
database "PostgreSQL\norchestrator_outbox" as Outbox
participant "conversation-memory-service" as Memory
participant "conversation-audit-service" as Audit
participant "conversation-handoff-service" as Handoff
participant "whatsapp-bff" as BFF
queue Kafka
participant "WhatsApp Cloud API" as Meta

Dispatcher -> Outbox: claim batch\nFOR UPDATE SKIP LOCKED
Outbox --> Dispatcher: menor journey_version pendente

loop cada efeito
  alt memory projection
    Dispatcher -> Memory: JWT + tenant + Idempotency
  else audit
    Dispatcher -> Audit: JWT + tenant + Idempotency-Key
  else handoff
    Dispatcher -> Handoff: JWT + tenant + Idempotency-Key
  else resposta ao canal
    Dispatcher -> BFF: JWT + tenant + Idempotency-Key
    BFF -> BFF: SET NX pending no Redis
    BFF -> Meta: envia mensagem
    Meta --> BFF: messageId
    BFF -> BFF: completed:messageId
  else evento
    Dispatcher ->> Kafka: intent/state + trace + tenant
  end

  alt sucesso/duplicado
    Dispatcher -> Outbox: status=published
  else falha
    Dispatcher -> Outbox: status=failed\nnext_attempt_at com backoff
  end
end

note right of Outbox
Uma versão posterior não é liberada
enquanto existir efeito anterior não publicado.
end note
@enduml
```

## 3. Idempotência de simulação e confirmação

```plantuml
@startuml
hide footbox
autonumber

participant Agent
participant "Tool Service" as Tools
participant "Renegotiation Service" as Reneg
database "PostgreSQL\nrenegotiation_idempotency" as Idem
participant "Core Bancário Mock" as Core
database "Memória do processo\nCore idempotency" as CoreIdem

Agent -> Tools: simular_proposta
Tools -> Tools: policy por stage\ngera chave determinística
Tools -> Reneg: JWT governed_tool + Idempotency-Key
Reneg -> Reneg: valida policy_id == header
Reneg -> Idem: INSERT key/requestHash status=processing

alt chave nova no domínio
  Reneg -> Core: JWT + tenant + Idempotency-Key\nrequest
  Core -> Core: valida caller, assinatura e tenant
  Core -> CoreIdem: reserve(tenant, operation, key, hash)
  alt chave Core nova
    Core -> Core: executa mock
    Core -> CoreIdem: armazena resposta
    Core --> Reneg: resultado
  else replay igual
    CoreIdem --> Core: resposta armazenada
    Core --> Reneg: mesmo resultado
  else payload divergente
    Core --> Reneg: 409 non-retryable
  end
  Reneg -> Idem: status=completed + response
  Reneg --> Tools: resultado
else chave concluída no domínio
  Idem --> Reneg: resposta persistida
  Reneg --> Tools: mesmo resultado sem chamar Core
else mesma chave com outro request
  Reneg --> Tools: 409 conflict
else processing/failed ambíguo
  Reneg --> Tools: 409/reconciliação
end

Agent -> Tools: confirmar_acordo
Tools -> Tools: exige estágio e evidência
Tools -> Reneg: JWT governed_tool + policy_id
Reneg -> Reneg: revalida evidência
Reneg -> Core: JWT + tenant + Idempotency-Key
Core -> CoreIdem: reserva/replay/conflict
@enduml
```

A persistência PostgreSQL do domínio é a garantia durável. O store do Core é process-local e adiciona determinismo/defesa em profundidade durante homologação.

## 4. Retry de entrada e DLQ

```plantuml
@startuml
hide footbox
autonumber

queue "channel.webhook.received" as Input
participant "KafkaWebhookConsumerService" as Consumer
participant "conversation-orchestrator" as Orch
queue "channel.webhook.received.retry" as Retry
queue "channel.webhook.received.dlq" as DLQ

Input ->> Consumer: registro + traceparent
Consumer -> Consumer: lê x-delivery-attempt

alt JSON inválido ou payload nulo
  Consumer ->> DLQ: payload + reason/source
  DLQ --> Consumer: publish confirmado
  Consumer -> Input: commit offset
else Orchestrator retorna 409/erro
  Consumer ->> Retry: payload + tentativa incrementada
  Retry --> Consumer: publish confirmado
  Consumer -> Input: commit offset original
  Retry ->> Consumer: nova entrega
else tentativas esgotadas
  Consumer ->> DLQ: payload + attempts + reason
  DLQ --> Consumer: publish confirmado
  Consumer -> Retry: commit offset
else 202
  Consumer -> Input: commit offset
end

note right of Consumer
Se retry/DLQ falhar, o offset original
não é commitado e ocorre seek/replay.
end note
@enduml
```

## 5. Consulta de fatura/limite

Fluxo somente leitura, sem idempotência de negócio por desenho.

```plantuml
@startuml
hide footbox
autonumber

actor Cliente
participant "whatsapp-bff" as BFF
participant "conversation-orchestrator" as Orch
participant "agent-runtime-fatura-cartao" as Agent
participant "tool-service-cartao-credito" as Tools
participant "Core Bancário Mock\nCard API :9405" as Core

Cliente -> BFF: mensagem
BFF -> Orch: POST /messages
Orch -> Agent: POST /process\nJWT + tenant + StructuredState
Agent -> Agent: guard determinístico de CPF

alt CPF ausente
  Agent --> Orch: solicita CPF
else CPF informado
  Agent -> Tools: MCP + JWT tool_execution
  Tools -> Tools: caller == agent-runtime-fatura-cartao
  Tools -> Core: GET card/limit|invoice\nJWT + X-Tenant-Id
  Core -> Core: valida assinatura, audience,\nkid/sub, tenant e caller
  Core --> Tools: resultado de cartão
  Tools --> Agent: resultado
  Agent --> Orch: ReplyText + State
end

Orch --> BFF: 202 Accepted
BFF --> Cliente: resposta
@enduml
```

Diferenças para renegociação:

- sem serviço de domínio intermediário;
- autorização por identidade, não por estágio;
- sem `Idempotency-Key`, pois são consultas;
- CPF não é publicado em `agent.events` ou `tool.executed`.

## 6. Garantias e limites

| Aspecto | Garantia implementada |
|---|---|
| Entrada WhatsApp | ACK após persistência Kafka |
| Inbox | conclusão após estado e efeitos na mesma transação |
| Side effects | Outbox at-least-once + dedupe |
| Ordenação | lease, versão otimista, late-message e barrier |
| Tenant | UUID no header e claim assinada |
| Tools | allowlist/policy no Tool e domínio |
| Core | caller/tenant validados; mutações exigem chave |
| Simulação | PostgreSQL durável + replay process-local no Core |
| Confirmação | evidência assinada e idempotência no último hop |
| Memória | unicidade `(tenantId, externalMessageId)` |
| Audit/Handoff | unicidade `(tenant_id, idempotency_key)` |

Limites:

- idempotência do Core é perdida no restart;
- HS256 continua simétrico;
- Handoff não transfere para plataforma humana;
- receiver Alertmanager é local/nulo;
- E2E multi-repositório precisa ser executado e registrado antes de promoção.
