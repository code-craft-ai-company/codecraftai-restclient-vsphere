# Requirements

## Introduction

The `vsphere-guest-customization` feature adds guest-OS customization on `GuestGroup`
so the provisioning engine can set hostname, network configuration, DNS, SSH keys,
and arbitrary first-boot commands on a freshly cloned or deployed VM. On Linux the
implementation renders cloud-init datasource files; on Windows it renders a sysprep
unattend.xml.

Guest customization is vSphere's user-data equivalent — the same place
`automojo-provisioning` injects `tailscale up …` for VPN bring-up (per §6.3 of
`PLAN-VPN-AND-CLOUD-PROVISIONING.md`).

---

## Requirements

### Requirement 1: Apply Customization Spec

**User Story:** As a provisioning engine, I want to apply a typed
`VmGuestCustomizationSpec` to a VM and have vCenter render the appropriate guest-OS
artifacts.

#### Acceptance Criteria

1. WHEN `Guest.apply_guest_customization_spec(vm=..., spec=..., aspects=...)` is
   called THE SYSTEM SHALL issue the corresponding vCenter endpoint and return a
   `VSphereTaskHandle`.
2. WHEN the VM's detected guest OS is Linux THE SYSTEM SHALL render a cloud-init
   payload from the spec.
3. WHEN the VM's detected guest OS is Windows THE SYSTEM SHALL render a sysprep
   unattend.xml payload from the spec.
4. WHEN the detected guest OS is neither Linux nor Windows THE SYSTEM SHALL raise
   `SemanticError`.

---

### Requirement 2: Hostname Rendering

#### Acceptance Criteria

1. THE SYSTEM SHALL accept hostnames matching DNS-label rules (lowercase letters,
   digits, hyphens; 1–63 chars; not starting or ending with hyphen).
2. WHEN the hostname violates DNS-label rules THE SYSTEM SHALL raise `SemanticError`
   before issuing the request.

---

### Requirement 3: Network Configuration

#### Acceptance Criteria

1. THE SYSTEM SHALL accept a list of `NetworkConfig(nic_index, mode: DHCP|STATIC,
   ipv4_address, ipv4_prefix, ipv4_gateway, ipv6_address, ipv6_prefix,
   ipv6_gateway)` entries on the spec.
2. WHEN `mode` is `STATIC` and any address field is empty THE SYSTEM SHALL raise
   `SemanticError`.
3. WHEN `mode` is `DHCP` and address fields are provided THE SYSTEM SHALL raise
   `SemanticError` (inconsistent input).

---

### Requirement 4: SSH Keys and First-Boot Commands

#### Acceptance Criteria

1. WHEN `ssh_authorized_keys` is provided THE SYSTEM SHALL inject them into
   cloud-init `users` (Linux only); Windows raises `SemanticError` if SSH keys are
   set with no compatible role.
2. WHEN `run_command_scripts` is provided THE SYSTEM SHALL render them into
   cloud-init `runcmd` (Linux) or sysprep first-boot RunSynchronousCommand (Windows).
3. THE SYSTEM SHALL preserve the order of commands as supplied by the caller.
