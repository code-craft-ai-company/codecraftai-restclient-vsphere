# Requirements

## Introduction

The `vsphere-events-stream` feature adds an `Events.stream(filter, aspects)` method
that yields `EventRecord` DTOs as they arrive from vCenter. Useful for landscape
watchers and for provisioning verification (e.g. observing a "VM deployed"
event in addition to polling task state).

---

## Requirements

### Requirement 1: Stream Events

**User Story:** As a watcher, I want a generator that yields vCenter events
matching a filter, so I can react to events without polling task ids.

#### Acceptance Criteria

1. WHEN `Events.stream(filter=EventFilter(...), aspects=...)` is called THE SYSTEM
   SHALL return a generator that yields `EventRecord` DTOs.
2. WHEN the generator is iterated THE SYSTEM SHALL poll the vCenter events
   endpoint at `aspects.poll_interval` and yield any new events since the last
   poll.
3. WHEN the generator is closed (via `.close()` or by exiting a `with` block) THE
   SYSTEM SHALL cease polling immediately.

---

### Requirement 2: Filter Shape

#### Acceptance Criteria

1. THE SYSTEM SHALL accept `EventFilter(event_types, severities, target_kind,
   target_id, since)`.
2. WHEN the filter is empty THE SYSTEM SHALL yield all events.
3. WHEN `since` is provided THE SYSTEM SHALL skip events with `timestamp < since`.

---

### Requirement 3: Backpressure

#### Acceptance Criteria

1. WHEN the consumer iterates slower than vCenter produces events THE SYSTEM SHALL
   buffer at most `aspects.event_buffer_limit` events (default 1000) before
   dropping the oldest and emitting a structured log warning.
2. WHEN events are dropped THE SYSTEM SHALL increment a per-stream counter
   accessible via `stream.dropped_count`.
