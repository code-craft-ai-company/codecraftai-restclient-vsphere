# Implementation Plan — VSphere API Groups Migration

## Migration scaffolding

- [x] 1. Create `apigroups/__init__.py` exporting every `*Group` class by name.

- [x] 2. Implement `BaseGroup` (was `BaseExt`) — common helpers shared by other
  groups (filter-state-aware URL composition, paging helpers if any).

## Migrate the 29 public groups

- [x] 3. `CertificateManagementGroup` (was `CertificateManagementExt`).

- [x] 4. `ClusterGroup` (was `ClusterExt`).

- [x] 5. `ComputeGroup` (was `ComputeExt`).

- [x] 6. `ContentGroup` (was `ContentExt`).

- [x] 7. `CryptoManagerGroup` (was `CryptoManagerExt`).

- [x] 8. `DatacenterGroup` (was `DatacenterExt`).

- [x] 9. `DatastoreGroup` (was `DatastoreExt`).

- [x] 10. `DeploymentGroup` (was `DeploymentExt`).

- [x] 11. `FolderGroup` (was `FolderExt`).

- [x] 12. `GuestGroup` (was `GuestExt`).

- [x] 13. `HostGroup` (was `HostExt`).

- [x] 14. `HvcGroup` (was `HvcExt`).

- [x] 15. `IdentityGroup` (was `IdentityExt`).

- [x] 16. `InventoryGroup` (was `InventoryExt`).

- [x] 17. `IsoGroup` (was `IsoExt`).

- [x] 18. `LcmGroup` (was `LcmExt`).

- [x] 19. `NamespaceManagementGroup` (was `NamespaceManagementExt`).

- [x] 20. `NamespacesGroup` (was `NamespacesExt`).

- [x] 21. `NetworkGroup` (was `NetworkExt`).

- [x] 22. `OvfGroup` (was `OvfExt`).

- [x] 23. `ResourcePoolGroup` (was `ResourcePoolExt`).

- [x] 24. `ServicesGroup` (was `ServicesExt`).

- [x] 25. `StorageGroup` (was `StorageExt`).

- [x] 26. `SystemConfigGroup` (was `SystemConfigExt`).

- [x] 27. `TaggingGroup` (was `TaggingExt`).

- [x] 28. `TokenServiceGroup` (was `TokenServiceExt`).

- [x] 29. `TopologyGroup` (was `TopologyExt`).

- [x] 30. `TrustedInfrastructureGroup` (was `TrustedInfrastructureExt`).

- [x] 31. `VmGroup` (was `VmExt`).

## Cross-cutting

- [x] 32. Add the `aspects: AspectsRest = DEFAULT_VSPHERE_ASPECTS` keyword-only
  parameter to every public method on every group.

- [x] 33. Convert every legacy positional parameter to keyword-only in the new
  signatures.

- [x] 34. Replace every raw `dict` / `requests.Response` return with the typed DTO
  from `model/` (cross-spec dependency on `vsphere-data-model-and-specs`).

- [x] 35. Replace every async-task call site with a `VSphereTaskHandle` return
  (cross-spec dependency on `vsphere-task-handle`).

## Tests

- [x] 36. Structural test — assert all 30 modules / classes exist and inherit
  `RestApiGroup`.

- [x] 37. API parity tests — per `*Group`, assert every legacy public method has a
  counterpart on the new class (frozen-snapshot driven).

- [x] 38. Aspects forwarding tests — sample methods per group; assert default and
  override behaviour.

- [x] 39. Property tests (hypothesis) — URL composition correctness:
  - single-slash invariant
  - percent-encoding of unsafe characters
  - alphabetical ordering of query parameters
  - determinism of composition
  - SemanticError raised at registration for malformed `BASE_LEAF`

- [x] 40. No-decorator audit — structural test that scans `apigroups/` for any
  behaviour-modifying decorator and fails if one is found.
