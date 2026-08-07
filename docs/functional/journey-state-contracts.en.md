# Journey State Contracts

## Objective

Deterministically validate the state returned by each Agent Runtime. The executable source is `contracts/functional/journeys.yaml`.

## Structure

Each journey declares:

- schema version;
- initial state;
- known states;
- required fields by state;
- valid transitions;
- functional event for each transition;
- invariants.

## Renegotiation

```text
Started
  → CustomerIdentified
  → ContractSelectionPending ─┐
  → ContractSelected ◀────────┘
  → EligibilityChecked
  → ProposalAvailable
  → ProposalSelected
  → AgreementConfirmed
  → DocumentAvailable
```

`HandoffRequested` is a controlled exit that may occur before completion.

### Invariants

- transitions are progressive, except for session reset;
- financial identifiers cannot be derived from a partial tax ID;
- mutable operations require explicit confirmation;
- persisted state must contain the fields required by the stage;
- a proposal must have an expiration/validity period;
- a document can only exist after an agreement is confirmed.

## Card

```text
Started
  → CustomerIdentified
  ↺ CardInformationDelivered
  → ReturnedToMenu
  → HandoffRequested
```

The inquiry does not create a permanent transactional stage. The verified tax ID remains in `structured_state` during the session.

## Compatibility

- adding an optional field: compatible change;
- adding a new reachable state without changing existing states: minor version;
- removing or renaming a state/required field: major version;
- the Orchestrator must persist `stateSchemaVersion` with the state;
- a migration must be defined before changing a journey that has active conversations.
