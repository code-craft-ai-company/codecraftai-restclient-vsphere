# Implementation Plan — VSphere Data Model and Specs

## model/ (response DTOs)

- [x] 1. `VirtualMachineSummary` and `VirtualMachineInfo` in `model/vm.py`.
- [x] 2. `DatacenterSummary`, `FolderSummary`, `ClusterSummary`, `HostSummary` in
  `model/summary.py`.
- [x] 3. `EventRecord` in `model/event.py`.
- [x] 4. `NetworkSummary`, `DistributedSwitchSummary` in `model/network.py`.
- [x] 5. `DatastoreSummary`, `DatastoreInfo` in `model/datastore.py`.
- [x] 6. `OvfDescriptor`, `OvfDeployResult` in `model/ovf.py`.
- [x] 7. Re-export `TaskInfo` from `model/task.py`.

## specs/ (request payloads)

- [x] 8. `VmCreateSpec` in `specs/vmcreate.py`.
- [x] 9. `VmCloneSpec` in `specs/vmclone.py` (NEW).
- [x] 10. `VmSnapshotSpec` in `specs/vmsnapshot.py` (NEW).
- [x] 11. `VmPowerActionSpec` in `specs/vmpoweraction.py` (NEW).
- [x] 12. `VmGuestCustomizationSpec` in `specs/vmguestcustomization.py` (NEW).
- [x] 13. `VmPlacementSpec` in `specs/vmplacement.py`.
- [x] 14. `VmHardwareSpec` in `specs/vmhardware.py`.
- [x] 15. `VmStorageSpec` in `specs/vmstorage.py`.

## enums/ (reference data)

- [x] 16. `GuestOs` enum in `enums/guestos.py` (migrate from
  `metasphere/vmguestos.py`).
- [x] 17. `HardwareVersion` enum in `enums/hardwareversion.py` (migrate from
  `metasphere/vmhardware.py`).
- [x] 18. `PowerState` enum in `enums/powerstate.py`.
- [x] 19. `VmPowerAction` enum in `enums/vmpoweraction.py`.

## Tests

- [x] 20. Round-trip `from_dict(to_dict(obj)) == obj` tests for every DTO and spec.
- [x] 21. Field-type validation tests — mismatch and missing-required raise.
- [x] 22. Enum coverage tests — frozen snapshot of API string values.
- [x] 23. Migration-completeness tests — every legacy `metasphere/*` constant
  present in new `enums/`.
- [x] 24. New-specs tests — `VmCloneSpec`, `VmSnapshotSpec`, `VmPowerActionSpec`,
  `VmGuestCustomizationSpec` accept declared fields, reject missing required fields.
