# Implementation Plan — VSphere Task Handle

- [x] 1. Define `TaskState` enum and `TERMINAL_STATES` frozenset in
  `vspheretaskhandle.py`.

- [x] 2. Define `TaskInfo` dataclass (task_id, state, progress_percent, started_at,
  completed_at, description, target_kind, target_id, error).

- [x] 3. Define exceptions: `VSphereTaskFailedError`, `VSphereTaskTimeoutError`,
  `VSphereTaskNotCancellableError`.

- [x] 4. Implement `VSphereTaskHandle.__init__(task_id, client)` — no I/O.

- [x] 5. Implement `status(aspects=...)` — fresh GET to the tasks endpoint, parse
  into `TaskInfo`.

- [x] 6. Implement `wait(aspects=...)` per the design's poll-loop algorithm:
  - strict-timeout gate at the top of each iteration
  - single-shot termination on first terminal observation
  - state-transition logging at `aspects.logging_level`
  - sleep `aspects.poll_interval` between polls

- [x] 7. Implement `cancel(aspects=...)`:
  - happy path: issue cancellation endpoint
  - already-terminal: no-op
  - not-cancellable: raise `VSphereTaskNotCancellableError`

- [x] 8. Declare `ITaskHandle` conformance and verify with a runtime
  `isinstance` test.

## Tests

- [x] 9. Construction tests — no I/O; identifiers stored.

- [x] 10. Status tests — fresh GET per call; reclassification on transport error.

- [x] 11. Wait happy-path tests — `QUEUED → RUNNING → SUCCEEDED` convergence.

- [x] 12. Wait failure-path tests — `RUNNING → FAILED` raises with `TaskInfo`.

- [x] 13. Wait timeout tests — stuck `RUNNING` plus tight timeout raises before next
  GET.

- [x] 14. Cancellation tests — three branches.

- [x] 15. Protocol-conformance test — `isinstance(handle, ITaskHandle)` is `True`.

- [x] 16. Property tests (hypothesis) — poll-loop convergence under any task-state
  sequence:
  - any finite sequence containing a terminal state → terminates (returns or raises),
    never hangs
  - non-terminal prefix length bounds the iteration count
  - terminal not reached + finite timeout → `VSphereTaskTimeoutError` within
    `timeout + poll_interval`
  - first terminal observation wins; later states never observed
  - state-transition log line count equals distinct adjacent-state changes + 1
