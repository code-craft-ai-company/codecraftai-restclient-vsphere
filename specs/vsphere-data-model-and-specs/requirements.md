# Requirements

## Introduction

The `vsphere-data-model-and-specs` feature delivers the typed DTOs (`model/`),
request payload specs (`specs/`), and reference enumerations (`enums/`) used by every
`*Group` class in `automojo-restclient-vsphere`. It is the home for what was previously
split between the legacy `datastructures/model/`, `datastructures/specs/`, and
`metasphere/` trees in `automojo-landscaping`, now cleanly separated by purpose.

All DTOs and specs are `SchemaObject` subclasses (from the automojo schema library)
with `SchemaField` declarations, giving callers typed access plus `to_dict()` /
`from_dict()` for serialisation.

This spec covers only the data shapes. The methods that produce or consume them are
owned by `vsphere-apigroups-migration` and the feature-specific specs.

---

## Requirements

### Requirement 1: Response DTOs (`model/`)

**User Story:** As a `*Group` author, I want a typed DTO for every vSphere response
payload I return, so callers never see raw dicts.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide DTOs for VM (`VirtualMachineSummary`,
   `VirtualMachineInfo`), summaries (`DatacenterSummary`, `FolderSummary`,
   `ClusterSummary`, `HostSummary`), tasks (`TaskInfo`), events (`EventRecord`),
   networks (`NetworkSummary`, `DistributedSwitchSummary`), datastores
   (`DatastoreSummary`, `DatastoreInfo`), and OVF (`OvfDescriptor`,
   `OvfDeployResult`).
2. WHEN any DTO is loaded from a dict via `from_dict(...)` THE SYSTEM SHALL validate
   each field against its declared type and raise on mismatch.
3. WHEN any DTO is serialised via `to_dict(...)` THE SYSTEM SHALL produce a payload
   accepted by `from_dict(...)` (round-trip).

---

### Requirement 2: Request Specs (`specs/`)

**User Story:** As a caller, I want typed request specs for VM create, clone,
snapshot, power action, and guest customization, so the call sites read like
configuration rather than dict-juggling.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide spec classes: `VmCreateSpec`, `VmCloneSpec`,
   `VmSnapshotSpec`, `VmPowerActionSpec`, `VmGuestCustomizationSpec`,
   `VmPlacementSpec`, `VmHardwareSpec`, `VmStorageSpec`.
2. WHEN a spec is constructed THE SYSTEM SHALL validate required fields and raise
   `SemanticError` on missing required values.
3. WHEN a spec is serialised THE SYSTEM SHALL emit a payload matching the vSphere
   API schema for that endpoint.

---

### Requirement 3: Reference Enumerations (`enums/`)

**User Story:** As a caller, I want reference data (guest OS catalog, hardware
versions, power states) as Python enums separated from the API DTOs, so I can
import them without dragging in the request/response shapes.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide `GuestOs` (migrated from `metasphere/vmguestos.py`),
   `HardwareVersion` (migrated from `metasphere/vmhardware.py`), and `PowerState`
   enumerations.
2. THE SYSTEM SHALL keep `enums/` free of any I/O, network calls, or schema
   library imports beyond what `Enum` requires.
3. THE SYSTEM SHALL provide a deterministic string value on each enum member
   matching the vSphere API string representation.

---

### Requirement 4: New Specs Required for Provisioning

**User Story:** As the `automojo-provisioning` `venue-vsphere` author, I want the
new specs (`VmCloneSpec`, `VmSnapshotSpec`, `VmPowerActionSpec`,
`VmGuestCustomizationSpec`) that the legacy client did not provide, so I can drive
the provisioning lifecycle.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide `VmCloneSpec(source_vm_id, target_name, placement,
   power_on_after, customization_spec_ref)`.
2. THE SYSTEM SHALL provide `VmSnapshotSpec(name, description, memory: bool,
   quiesce: bool)`.
3. THE SYSTEM SHALL provide `VmPowerActionSpec(action: VmPowerAction)` where
   `VmPowerAction ∈ {POWER_ON, POWER_OFF, SUSPEND, RESET, GUEST_SHUTDOWN,
   GUEST_REBOOT}`.
4. THE SYSTEM SHALL provide `VmGuestCustomizationSpec(hostname, dns_servers,
   dns_search, network_configs, ssh_authorized_keys, run_command_scripts)`.
