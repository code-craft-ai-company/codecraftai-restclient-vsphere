# Implementation Plan — VSphere VM Lifecycle Waiters

- [x] 1. Define `VSphereWaitTimeoutError` and `VSphereWaitInvalidStateError` in
  `apigroups/waiters.py`; re-export at package root.

- [x] 2. Implement `VmGroup.wait_for_power_state(vm, desired, aspects=...)`.

- [x] 3. Implement `GuestGroup.wait_for_tools_ready(vm, aspects=...)`.

- [x] 4. Implement `GuestGroup.wait_for_ip_address(vm, nic_index=0, aspects=...)`
  with IPv4/IPv6 selection via `aspects.ip_family`.

- [x] 5. Tests — power-state waiter (happy / timeout / first-poll-hit).

- [x] 6. Tests — tools-ready waiter (happy / timeout / immediate).

- [x] 7. Tests — IP-address waiter (IPv4 happy, IPv6 happy, timeout, mid-wait
  power-off raises `VSphereWaitInvalidStateError`).
