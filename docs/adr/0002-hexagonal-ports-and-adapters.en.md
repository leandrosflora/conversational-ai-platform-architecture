# ADR 0002: Hexagonal Architecture (Ports & Adapters) in .NET Services

## Status

Accepted and implemented (retrospective — this ADR documents the structural convention adopted in all .NET services from the beginning of each project).

**Affected services:** [`whatsapp-bff`](../services/whatsapp-bff.md), [`conversation-orchestrator`](../services/conversation-orchestrator.md), [`renegotiation-service`](../services/renegotiation-service.md).

## Context

The platform has three .NET services (`whatsapp-bff`, `conversation-orchestrator`, `renegotiation-service`) that need to replace infrastructure adapters (HTTP, Kafka, in-memory persistence) without rewriting application logic — for example, replacing the Orchestrator's in-memory session with Redis in the future, or replacing Kafka with another broker without changing use cases.

## Decision

All three .NET services follow the same folder structure corresponding to hexagonal architecture (ports & adapters):

- `Domain/` — pure domain models with no infrastructure dependency.
- `Application/Ports/Inbound/` — interfaces called by inbound adapters, such as `IIngestMessageUseCase`, `IProcessInboundWebhookUseCase`.
- `Application/Ports/Outbound/` — interfaces used by the application to communicate with the external world, such as `IAgentRuntimeClient`, `IChannelEventPublisher`, `IConversationSessionStore`.
- `Application/UseCases/` — inbound-port implementations that depend only on interfaces and never concrete types from `Adapters/`.
- `Adapters/Inbound/` — adapters translating an external protocol (HTTP, Kafka consumer) into an inbound-port call.
- `Adapters/Outbound/` — adapters implementing outbound ports against a concrete technology (HTTP client, Kafka producer/consumer, in-memory storage).
- `Configuration/` — option classes (`IOptions<T>`), one per external integration.

Dependency injection in `Program.cs` is the only place that connects an interface to a concrete implementation.

## Positive consequences

- Use cases can be tested in isolation with mocked ports, as confirmed by the existing `*.Tests` suites that mock `IAgentRuntimeClient`, `IChannelEventPublisher`, and others through Moq.
- Replacing an adapter, such as in-memory session → Redis, does not require changes in `Application/`.
- The same convention across three services reduces the cognitive load of navigating between them.

## Negative consequences

- More files and indirection than a simple MVC structure, even for services with little domain logic today, such as the mostly pass-through `renegotiation-service`.
- The convention was not explicitly documented until this ADR, so new contributors previously had to infer the pattern from the folder structure.
