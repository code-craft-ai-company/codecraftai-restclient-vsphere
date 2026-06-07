# Design

## Overview

The waiters compose the generic poll-loop primitives provided by `codecraftai-waiting`
and the typed return shapes provided by `vsphere-data-model-and-specs`. They live
as methods on the relevant API groups (`VmGroup` for power state; `GuestGroup` for
tools-ready and IP-address) rather than as free functions, so callers discover them
naturally through the same client surface as the rest of the API.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│   VmGroup.wait_for_power_state(...)                  │
│   GuestGroup.wait_for_tools_ready(...)               │
│   GuestGroup.wait_for_ip_address(...)                │
└─────────────────────┬────────────────────────────────┘
                      │ delegates to
                      ▼
┌──────────────────────────────────────────────────────┐
│   codecraftai-waiting.PollLoop                          │
│   - interval, timeout from AspectsRest               │
│   - typed predicate + result extractor               │
└──────────────────────────────────────────────────────┘
```

---

## Data Model

```python
class VSphereWaitTimeoutError(Exception):
    """Raised when a waiter exceeds aspects.timeout_seconds."""
    observed: object  # the last observation


class VSphereWaitInvalidStateError(Exception):
    """Raised when a waiter observes an obviously invalid state mid-wait
    (e.g. VM powered off during wait_for_ip_address)."""
    observed: object
```

---

## Module Layout

The waiters are methods added to existing modules:

- `apigroups/vmgroup.py` — `wait_for_power_state`
- `apigroups/guestgroup.py` — `wait_for_tools_ready`, `wait_for_ip_address`

Shared exceptions live in `apigroups/waiters.py` and are re-exported from the
package root.

---

## See Also

- `codecraftai-waiting` — poll-loop primitive.
- `vsphere-task-handle` — sibling sync-poll pattern (different scope: tasks vs
  runtime states).
- `vsphere-data-model-and-specs` — `PowerState` and related enums.

---

## Testing Strategy

- Drive a `FakeVmStateSource` keyed on a scripted sequence and verify the waiter
  converges, times out, or raises `VSphereWaitInvalidStateError` as appropriate.
- Time is mocked; no sleeps in tests.
- Edge cases: target reached on first poll, target reached on last poll before
  timeout, target never reached, invalid mid-wait state (power-off during
  IP-address wait).
