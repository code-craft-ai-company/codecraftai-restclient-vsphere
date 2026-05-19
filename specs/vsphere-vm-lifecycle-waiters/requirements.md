# Requirements

## Introduction

The `vsphere-vm-lifecycle-waiters` feature adds VM-specific waiter methods to
`VmGroup` and `GuestGroup` that poll until specific runtime conditions are met:
power state, VMware Tools readiness, and IP address allocation. The waiters compose
the generic `automojo-waiting` package's poll-loop primitives and accept `AspectsRest`
for interval and timeout control.

These waiters are required by `automojo-provisioning/venues/vsphere` to implement
the verification stage of `apply` (per §6.3 of `PLAN-VPN-AND-CLOUD-PROVISIONING.md`).

---

## Requirements

### Requirement 1: Wait for Power State

**User Story:** As a provisioning engine, I want to block until a VM reaches a
desired power state.

#### Acceptance Criteria

1. WHEN `Vm.wait_for_power_state(vm=..., desired=PowerState.POWERED_ON, aspects=...)`
   is called THE SYSTEM SHALL poll the VM's power state at `aspects.poll_interval`
   until it equals `desired`.
2. WHEN `aspects.timeout_seconds` elapses without reaching `desired` THE SYSTEM SHALL
   raise `VSphereWaitTimeoutError` with the last observed power state attached.
3. WHEN `desired` is reached THE SYSTEM SHALL return the final `PowerState`.

---

### Requirement 2: Wait for VMware Tools Ready

**User Story:** As a provisioning engine, I want to block until VMware Tools inside
the guest is reporting `RUNNING`, so I know guest-side commands and IP reporting
are available.

#### Acceptance Criteria

1. WHEN `Guest.wait_for_tools_ready(vm=..., aspects=...)` is called THE SYSTEM SHALL
   poll the guest tools status until it equals `RUNNING`.
2. WHEN the timeout elapses THE SYSTEM SHALL raise `VSphereWaitTimeoutError` with
   the last observed status.
3. WHEN tools is already `RUNNING` at first poll THE SYSTEM SHALL return immediately.

---

### Requirement 3: Wait for IP Address

**User Story:** As a provisioning engine, I want to block until the guest reports an
IP address on its primary NIC, so I can hand the address to landscaping.

#### Acceptance Criteria

1. WHEN `Guest.wait_for_ip_address(vm=..., nic_index=0, aspects=...)` is called THE
   SYSTEM SHALL poll until a non-empty IPv4 address is reported for the given NIC.
2. WHEN `aspects.ip_family` is set to `IPV6` THE SYSTEM SHALL wait for an IPv6
   address instead.
3. WHEN the timeout elapses without an address THE SYSTEM SHALL raise
   `VSphereWaitTimeoutError`.
4. WHEN the VM is powered off during the wait THE SYSTEM SHALL raise
   `VSphereWaitInvalidStateError` with the observed power state.
