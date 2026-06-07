# Design

## Overview

The events stream is a Python generator backed by a poll loop against the vCenter
events endpoint. It yields typed `EventRecord` DTOs (from
`vsphere-data-model-and-specs`) and is filterable. The generator supports clean
shutdown via `.close()` and exposes a backpressure counter for observability.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│   EventsGroup.stream(filter, aspects) → EventStream        │
└─────────────────────┬──────────────────────────────────────┘
                      │ implemented by
                      ▼
┌────────────────────────────────────────────────────────────┐
│   EventStream (generator-like)                             │
│   __iter__, __next__, close, dropped_count                 │
│                                                            │
│   internal poll loop:                                      │
│     while not closed:                                      │
│       new = fetch_events_since(last_seen, filter)          │
│       for ev in new:                                       │
│         buffer.append(ev); enforce buffer_limit            │
│         yield ev (via __next__)                            │
│       last_seen = new[-1].timestamp if new else last_seen  │
│       sleep(aspects.poll_interval)                         │
└────────────────────────────────────────────────────────────┘
```

---

## Data Model

```python
@dataclass
class EventFilter:
    event_types: Optional[List[str]] = None
    severities: Optional[List[str]] = None      # "INFO", "WARNING", "ERROR"
    target_kind: Optional[str] = None           # "VM", "Host", "Datastore", ...
    target_id: Optional[str] = None
    since: Optional[datetime] = None


class EventStream:
    dropped_count: int

    def __iter__(self) -> "EventStream": ...
    def __next__(self) -> EventRecord: ...
    def close(self) -> None: ...
```

---

## Module Layout

```
source/packages/ccai/restclient/vsphere/
├── apigroups/eventsgroup.py     # (new) EventsGroup with stream()
├── apigroups/eventstream.py     # EventStream
└── specs/eventfilter.py         # EventFilter
```

`EventsGroup` is added alongside the migrated groups; it does not have a legacy
`*Ext` counterpart.

---

## See Also

- `vsphere-data-model-and-specs` — `EventRecord` DTO.
- `vsphere-task-handle` — sibling poll-based primitive (different purpose: tasks vs
  events).

---

## Testing Strategy

- Stream tests against a `FakeEventsSource` driven by scripted event batches.
- Filter tests — each filter field constrains the yielded set as expected.
- Backpressure tests — overflow triggers drop counter and structured log warning.
- Close tests — `.close()` halts polling deterministically.
- No live vCenter required.
