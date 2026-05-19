# Implementation Plan — VSphere Events Stream

- [x] 1. Define `EventFilter` in `specs/eventfilter.py`.

- [x] 2. Implement `EventStream` class in `apigroups/eventstream.py` with
  `__iter__`, `__next__`, `close`, `dropped_count`.

- [x] 3. Implement `EventsGroup.stream(filter, aspects)` returning an `EventStream`.

- [x] 4. Register `EventsGroup` on `VSphereClient` as `Events` property.

- [x] 5. Tests — happy stream against `FakeEventsSource`.

- [x] 6. Tests — each filter field constrains the yield set.

- [x] 7. Tests — backpressure overflow triggers drop counter + log warning.

- [x] 8. Tests — `.close()` halts polling deterministically.
