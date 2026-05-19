# Requirements

## Introduction

The `vsphere-task-handle` feature delivers `VSphereTaskHandle`, the synchronous,
Aspects-controlled poll handle returned by every long-running vSphere API call.
vSphere operations such as `Vm.create`, `Vm.clone`, `Vm.delete`, `Ovf.deploy`,
`ContentLibrary.deploy`, and many others are asynchronous on the wire: the initial
call returns a task identifier and the result must be polled.

Per the design decision in §6.6 of `PLAN-VPN-AND-CLOUD-PROVISIONING.md`, the client
exposes these tasks **synchronously** via poll-with-Aspects — no `asyncio`. Aspects
controls poll interval, timeout, and logging on every wait call.

`VSphereTaskHandle` implements the `ITaskHandle` protocol from `automojo-interfaces`
and is built on the reusable `TaskHandle` base in `automojo-restclient-base`. It
adds vSphere-specific concerns: task-info parsing (`TaskInfo`, `TaskState`),
progress reporting, and known-state transitions.

---

## Requirements

### Requirement 1: Handle Construction

**User Story:** As a `*Group` author, I want to construct a `VSphereTaskHandle` from
a task identifier and the originating client, so I can return it from any
long-running API call.

#### Acceptance Criteria

1. WHEN a `*Group` constructs `VSphereTaskHandle(task_id=..., client=...)` THE
   SYSTEM SHALL store the task id and a back-reference to the client.
2. WHEN construction succeeds THE SYSTEM SHALL NOT perform any network I/O.

---

### Requirement 2: Status Polling

**User Story:** As a caller, I want to query the current task status without
blocking, so I can implement custom progress UIs.

#### Acceptance Criteria

1. WHEN `handle.status(aspects=...)` is called THE SYSTEM SHALL issue a single GET
   against the vSphere tasks endpoint for this task id and return a `TaskInfo`.
2. WHEN the GET fails with a transport error THE SYSTEM SHALL raise the error after
   reclassification via the standard `RestClientBase` mechanism.
3. THE SYSTEM SHALL NOT cache the status — every call to `status()` is a fresh GET.

---

### Requirement 3: Wait for Terminal State

**User Story:** As a caller, I want to block until the task reaches a terminal state
(SUCCEEDED, FAILED, or ERROR), so I can write straight-line provisioning code.

#### Acceptance Criteria

1. WHEN `handle.wait(aspects=...)` is called THE SYSTEM SHALL poll at the interval
   declared by `aspects.poll_interval` (default 2.0 seconds) until the returned
   `TaskInfo.state` is one of `SUCCEEDED`, `FAILED`, or `ERROR`.
2. WHEN the poll loop exceeds `aspects.timeout_seconds` THE SYSTEM SHALL raise
   `VSphereTaskTimeoutError` with the last observed `TaskInfo` attached.
3. WHEN the task reaches `SUCCEEDED` THE SYSTEM SHALL return the final `TaskInfo`.
4. WHEN the task reaches `FAILED` or `ERROR` THE SYSTEM SHALL raise
   `VSphereTaskFailedError` with the final `TaskInfo` attached.
5. WHILE polling THE SYSTEM SHALL log progress at the level declared by
   `aspects.logging_level` (default INFO) on every state transition (but not on
   identical-state polls).

---

### Requirement 4: Cancellation

**User Story:** As a caller, I want to cancel a running task when my workflow
decides the task is no longer needed.

#### Acceptance Criteria

1. WHEN `handle.cancel(aspects=...)` is called THE SYSTEM SHALL issue the
   vSphere-specific cancellation request for the task id.
2. WHEN the task is already in a terminal state THE SYSTEM SHALL NOT issue the
   cancellation and SHALL return without raising.
3. WHEN the underlying task type does not support cancellation THE SYSTEM SHALL
   raise `VSphereTaskNotCancellableError` with a clear message.

---

### Requirement 5: ITaskHandle Conformance

**User Story:** As a provisioning engine author, I want `VSphereTaskHandle` to
conform to `ITaskHandle` from `automojo-interfaces`, so I can drive task waits
generically across any provisioning venue.

#### Acceptance Criteria

1. THE SYSTEM SHALL declare `VSphereTaskHandle` as implementing the `ITaskHandle`
   protocol.
2. WHEN `isinstance(handle, ITaskHandle)` is evaluated at runtime THE SYSTEM SHALL
   return `True`.
3. WHEN the protocol shape evolves THE SYSTEM SHALL update `VSphereTaskHandle` to
   match — incompatible drift is rejected at type-check time.

---

### Requirement 6: Poll-Loop Convergence Under Any State Sequence

**User Story:** As a caller, I want guarantees about how the poll loop behaves under
any possible sequence of vSphere task states, so I can trust it under real
production conditions where state can ratchet, stall, or report `RUNNING` for
arbitrarily long.

#### Acceptance Criteria

1. THE SYSTEM SHALL guarantee that for any sequence of non-terminal states (e.g.
   `QUEUED → RUNNING → RUNNING → RUNNING → SUCCEEDED`) the wait converges to the
   final state and returns.
2. THE SYSTEM SHALL guarantee that if the state sequence contains any terminal
   state, the wait stops on the first terminal observation regardless of any later
   states the polling source might emit.
3. THE SYSTEM SHALL guarantee that progress is at least monotonic with respect to
   the count of polls — every iteration of the loop issues exactly one status GET.
4. THE SYSTEM SHALL guarantee that timeout enforcement is strict: if the wall-clock
   elapsed time at the start of any poll exceeds `aspects.timeout_seconds`, the
   wait raises `VSphereTaskTimeoutError` before issuing the next GET.
