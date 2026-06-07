# Design

## Overview

This feature delivers the three sibling packages under `codecraftai-restclient-vsphere`:
`model/` for response DTOs, `specs/` for request payloads, and `enums/` for
reference data. The split eliminates the legacy conflation between
`datastructures/` (mixed DTOs and specs) and `metasphere/` (reference data jammed
next to dynamic types). All DTOs and specs are `SchemaObject` subclasses; all
enums are plain `Enum` subclasses with deterministic vSphere-API string values.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         *Group classes                       │
│                                                              │
│   def list(...) -> List[VirtualMachineSummary]:              │
│       resp = self.request(...)                               │
│       return [VirtualMachineSummary.from_dict(d) for d in …] │
│                                                              │
│   def create(*, spec: VmCreateSpec, ...) -> VSphereTaskHandle│
│       payload = spec.to_dict()                               │
│       task_id = self.request("POST", ..., json=payload)      │
│       return VSphereTaskHandle(task_id, self.client)         │
└─────────────────────────┬────────────────────────────────────┘
                          │ depends on
                          ▼
┌────────────────┬─────────────────────┬───────────────────────┐
│   model/       │       specs/        │       enums/          │
│  (response     │   (request payload  │  (reference data:     │
│   DTOs)        │    specs)           │   guest OS, hardware  │
│                │                     │   version, power)     │
│  SchemaObject  │   SchemaObject      │   Enum                │
└────────────────┴─────────────────────┴───────────────────────┘
```

---

## Data Model

### `model/` (response DTOs)

| Class | Notes |
| --- | --- |
| `VirtualMachineSummary` | vm id, name, power_state, cpu_count, memory_mib |
| `VirtualMachineInfo` | full VM detail including hardware, network, storage |
| `DatacenterSummary` | id, name, datastore_folder, host_folder, network_folder, vm_folder |
| `FolderSummary` | id, name, type |
| `ClusterSummary` | id, name, ha_enabled, drs_enabled |
| `HostSummary` | id, name, connection_state, power_state |
| `TaskInfo` | re-exported from `vsphere-task-handle` for convenience |
| `EventRecord` | id, type, timestamp, severity, message, user, target |
| `NetworkSummary` | id, name, type (STANDARD_PORTGROUP, DISTRIBUTED_PORTGROUP, OPAQUE_NETWORK) |
| `DistributedSwitchSummary` | id, name, uuid, version |
| `DatastoreSummary` | id, name, type, capacity, free_space |
| `DatastoreInfo` | full datastore detail incl. accessible, multiple_host_access |
| `OvfDescriptor` | name, vendor, version, eula, properties, networks |
| `OvfDeployResult` | resource_id, deployable, error |

### `specs/` (request payloads)

| Class | Notes |
| --- | --- |
| `VmCreateSpec` | name, guest_os, hardware, placement, storage, networks |
| `VmCloneSpec` | source_vm_id, target_name, placement, power_on_after, customization_spec_ref |
| `VmSnapshotSpec` | name, description, memory, quiesce |
| `VmPowerActionSpec` | action: VmPowerAction |
| `VmGuestCustomizationSpec` | hostname, dns_servers, dns_search, network_configs, ssh_authorized_keys, run_command_scripts |
| `VmPlacementSpec` | datacenter, cluster, host, resource_pool, folder, datastore |
| `VmHardwareSpec` | cpu_count, cores_per_socket, memory_mib, hardware_version |
| `VmStorageSpec` | disks: List[VmDiskSpec] |

### `enums/`

| Enum | Notes |
| --- | --- |
| `GuestOs` | full vSphere guest OS catalog (migrated from `metasphere/vmguestos.py`) |
| `HardwareVersion` | `VMX_4` through `VMX_21` etc. (migrated from `metasphere/vmhardware.py`) |
| `PowerState` | `POWERED_ON`, `POWERED_OFF`, `SUSPENDED` |
| `VmPowerAction` | `POWER_ON`, `POWER_OFF`, `SUSPEND`, `RESET`, `GUEST_SHUTDOWN`, `GUEST_REBOOT` |

---

## Module Layout

```
source/packages/ccai/restclient/vsphere/
├── model/
│   ├── __init__.py
│   ├── vm.py            # VirtualMachineSummary, VirtualMachineInfo
│   ├── summary.py       # *Summary types
│   ├── task.py          # re-export from vspheretaskhandle
│   ├── event.py         # EventRecord
│   ├── network.py       # NetworkSummary, DistributedSwitchSummary
│   ├── datastore.py     # DatastoreSummary, DatastoreInfo
│   └── ovf.py           # OvfDescriptor, OvfDeployResult
├── specs/
│   ├── __init__.py
│   ├── vmcreate.py
│   ├── vmclone.py
│   ├── vmsnapshot.py
│   ├── vmpoweraction.py
│   ├── vmguestcustomization.py
│   ├── vmplacement.py
│   ├── vmhardware.py
│   └── vmstorage.py
└── enums/
    ├── __init__.py
    ├── guestos.py
    ├── hardwareversion.py
    ├── powerstate.py
    └── vmpoweraction.py
```

---

## See Also

- `vsphere-apigroups-migration` — `*Group` methods produce model DTOs and consume
  spec instances.
- `vsphere-task-handle` — exports `TaskInfo` re-used by `model/task.py`.
- `vsphere-guest-customization` — consumes `VmGuestCustomizationSpec`.
- `vsphere-content-library-deploy`, `vsphere-ovf-deploy` — consume the OVF DTOs.

---

## Testing Strategy

1. **Round-trip tests** — for every DTO and spec, assert `from_dict(to_dict(obj))
   == obj` over hand-curated example payloads.
2. **Field-type validation tests** — assert `from_dict` raises on type mismatch
   and on missing required fields.
3. **Enum coverage tests** — assert every enum member maps to a unique
   API-string value (no collisions, no missing members) by comparing the enum
   member set to a frozen snapshot of vSphere API string values.
4. **Migration-completeness tests** — for every legacy `metasphere/*` constant,
   assert the corresponding entry exists in the new `enums/` module.
5. **Provisioning new-specs tests** — assert the four new specs
   (`VmCloneSpec`, `VmSnapshotSpec`, `VmPowerActionSpec`,
   `VmGuestCustomizationSpec`) accept their declared fields and reject missing
   required ones.

No live vCenter required.
