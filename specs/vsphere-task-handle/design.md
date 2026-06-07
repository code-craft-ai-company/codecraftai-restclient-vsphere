# Design

## Overview

`VSphereTaskHandle` is the synchronous poll handle returned by every long-running
vSphere API call. It conforms to the `ITaskHandle` protocol declared in
`codecraftai-interfaces` and reuses the generic `TaskHandle` base implemented in
`codecraftai-restclient-base` for the poll-loop scaffolding; the vSphere-specific
subclass adds task-info parsing, the terminal-state set, the cancellation endpoint,
and the typed exceptions.

The decision to expose tasks synchronously (rather than via `asyncio`) is fixed in
§6.6 of `PLAN-VPN-AND-CLOUD-PROVISIONING.md`: every other ccai API is
sync-with-Aspects, and consistency outweighs the small concurrency win from async.
Callers needing concurrency drive multiple `VSphereTaskHandle.wait` calls on threads
or use the higher-level Aspects-based futures pattern that lives in the
provisioning layer.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│            *Group method (e.g. VmGroup.create)               │
│   - issues async POST to vCenter                             │
│   - extracts task_id from the response                       │
│   - returns VSphereTaskHandle(task_id, client)               │
└─────────────────────────┬────────────────────────────────────┘
                          │ returns
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  VSphereTaskHandle                           │
│   status(aspects)  → fresh GET → TaskInfo                    │
│   wait(aspects)    → poll loop with timeout                  │
│   cancel(aspects)  → cancellation endpoint                   │
└─────────────────────────┬────────────────────────────────────┘
                          │ uses
                          ▼
┌──────────────────────────────────────────────────────────────┐
│        TaskHandle (codecraftai-restclient-base)                 │
│   - generic poll loop                                        │
│   - Aspects-controlled interval/timeout/logging              │
│   - state-transition logging                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Data Model

```python
class TaskState(Enum):
    QUEUED    = "QUEUED"
    RUNNING   = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED    = "FAILED"
    ERROR     = "ERROR"

TERMINAL_STATES = frozenset({TaskState.SUCCEEDED, TaskState.FAILED, TaskState.ERROR})


@dataclass
class TaskInfo:
    task_id: str
    state: TaskState
    progress_percent: int           # 0..100
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    description: Optional[str]
    target_kind: Optional[str]
    target_id: Optional[str]
    error: Optional[dict]           # vSphere error payload when state is FAILED/ERROR


class VSphereTaskFailedError(Exception):
    """Raised when a task reaches FAILED or ERROR terminal state."""
    info: TaskInfo


class VSphereTaskTimeoutError(Exception):
    """Raised when wait() exceeds aspects.timeout_seconds."""
    info: TaskInfo


class VSphereTaskNotCancellableError(Exception):
    """Raised when cancel() is invoked on a task type that does not support it."""
```

---

## Module Layout

```
source/packages/ccai/restclient/vsphere/
├── vspheretaskhandle.py    # VSphereTaskHandle, TaskState, TaskInfo, exceptions
```

---

## Poll-Loop Algorithm

```
function wait(aspects):
    started = monotonic()
    last_state = None
    while True:
        if monotonic() - started > aspects.timeout_seconds:
            raise VSphereTaskTimeoutError(info=last_info)
        info = self.status(aspects=aspects)
        last_info = info
        if info.state != last_state:
            log(aspects.logging_level, "task {tid} state: {state}", ...)
            last_state = info.state
        if info.state in TERMINAL_STATES:
            if info.state == SUCCEEDED:
                return info
            raise VSphereTaskFailedError(info=info)
        sleep(aspects.poll_interval)
```

Key invariants:

1. **Strict timeout enforcement.** The timeout check is at the top of each iteration,
   before issuing the GET. A long-running GET cannot blow past the timeout silently.
2. **Single-shot termination.** The first terminal state ends the loop — later
   states are not consulted.
3. **Monotonic progress in iteration count.** Every iteration issues exactly one
   status GET (subject to the strict timeout gate).
4. **No state caching.** Every status call is a fresh GET; stale views never cause
   the loop to terminate prematurely.

---

## See Also

- `codecraftai-interfaces.itaskhandle` — protocol declaration.
- `codecraftai-restclient-base.taskhandle` — generic poll-loop base class.
- `vsphere-apigroups-migration` — every async-bearing group method returns a
  `VSphereTaskHandle`.
- `vsphere-vm-lifecycle-waiters` — VM-specific waiters that compose `wait()`.

---

## Testing Strategy

1. **Construction tests** — no I/O on construct; task_id and client are stored.

2. **Status tests** — fresh GET per call; reclassification on transport error;
   correct `TaskInfo` parsing.

3. **Wait happy-path tests** — drive a fake polling source through scripted state
   sequences (`QUEUED → RUNNING → SUCCEEDED`, etc.) and assert convergence.

4. **Wait failure-path tests** — `RUNNING → FAILED` raises `VSphereTaskFailedError`
   with the final `TaskInfo` attached.

5. **Wait timeout tests** — a stuck `RUNNING` source plus a tight timeout raises
   `VSphereTaskTimeoutError` before issuing the next GET.

6. **Cancellation tests** — happy path, already-terminal short-circuit,
   not-cancellable error.

7. **Protocol conformance** — `isinstance(handle, ITaskHandle)` returns `True`.

8. **Property tests (hypothesis) — poll-loop convergence under any task-state
   sequence:**
   - For any finite sequence of `TaskState` values that contains at least one
     terminal state, `wait(aspects=loose_timeout)` terminates by returning
     `SUCCEEDED` info or by raising `VSphereTaskFailedError` — never hangs.
   - For any finite sequence of non-terminal states followed by a single terminal
     state, the number of poll iterations is bounded above by
     `len(non_terminal_prefix) + 1`.
   - For any sequence ending in `RUNNING` (no terminal reached) and any
     `timeout_seconds > 0`, `wait` raises `VSphereTaskTimeoutError` within
     `timeout_seconds + poll_interval` wall-clock time.
   - For two terminal states in the sequence (e.g. `SUCCEEDED` followed by
     `FAILED`), the loop terminates on the first observation only — the second
     terminal state is never observed.
   - State-transition logging is monotonic: the number of log lines emitted equals
     the number of distinct adjacent-state changes plus one (for the initial
     observation).

   The fake polling source is a deterministic generator parameterised by the
   sequence; the time source is mocked. No live vCenter required.
