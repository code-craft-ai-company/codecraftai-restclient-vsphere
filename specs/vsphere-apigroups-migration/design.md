# Design

## Overview

The migration moves the entire `ext/` tree from the legacy
`automojo-landscaping/services/vmware/vsphere/` location into `apigroups/` under
`automojo-interop-vsphere`. The migration is mechanical and exhaustive: each `*Ext`
class becomes a `*Group` class that inherits `RestApiGroup` from
`automojo-restclient-base`. URL composition, Aspects handling, content-type
negotiation, multipart upload, and response paging all come from the parent class —
no hand-rolled HTTP plumbing survives in any group.

The 29 modules in the legacy `ext/` directory map one-to-one to 29 modules in the new
`apigroups/` directory. The rename is the only structural change at the file level.
Inside each module, methods are rewritten to use `RestApiGroup` request helpers, to
take `aspects: AspectsRest = DEFAULT_VSPHERE_ASPECTS`, and to return typed DTOs from
the `model/` package owned by `vsphere-data-model-and-specs`.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                       VSphereClient                            │
│   @property Vm          → returns cached VmGroup               │
│   @property Cluster     → returns cached ClusterGroup          │
│   ... (29 properties)                                          │
└────────────────────────────┬───────────────────────────────────┘
                             │ each property returns
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                     <Name>Group(RestApiGroup)                  │
│   BASE_LEAF = "/api/..."  or  "/rest/..."                      │
│                                                                │
│   def list(self, *, filter_spec=None,                          │
│            aspects=DEFAULT_VSPHERE_ASPECTS) -> List[<DTO>]:    │
│       url = self.compose_url(...)                              │
│       resp = self.request("GET", url, aspects=aspects)         │
│       result = <DTO>.list_from_dict(resp.json())               │
│       return result                                            │
└────────────────────────────┬───────────────────────────────────┘
                             │ inherits from
                             ▼
┌────────────────────────────────────────────────────────────────┐
│         RestApiGroup (automojo-restclient-base)                │
│   - compose_url(...)                                           │
│   - request(method, url, aspects=...)                          │
│   - content-type negotiation, multipart upload, paging         │
└────────────────────────────────────────────────────────────────┘
```

---

## Migration Mapping — All 29 Modules

The exhaustive mapping from legacy `ext/*.py` to new `apigroups/*.py`. Every legacy
class drops the `Ext` suffix and gains a `Group` suffix; every legacy module is
renamed in lowercase with no underscores accordingly. The `VSphereClient` property
name shown in column 3 matches the legacy `VSphereAgent` property name unchanged.

| Legacy module (`ext/`) | Legacy class | New module (`apigroups/`) | New class | Client property |
| --- | --- | --- | --- | --- |
| `baseext.py` | `BaseExt` | `basegroup.py` | `BaseGroup` | (internal — base class) |
| `certificatemanagementext.py` | `CertificateManagementExt` | `certificatemanagementgroup.py` | `CertificateManagementGroup` | `CertificateManagement` |
| `clusterext.py` | `ClusterExt` | `clustergroup.py` | `ClusterGroup` | `Cluster` |
| `computeext.py` | `ComputeExt` | `computegroup.py` | `ComputeGroup` | `Compute` |
| `contentext.py` | `ContentExt` | `contentgroup.py` | `ContentGroup` | `Content` |
| `cryptomanagerext.py` | `CryptoManagerExt` | `cryptomanagergroup.py` | `CryptoManagerGroup` | `CryptoManager` |
| `datacenterext.py` | `DatacenterExt` | `datacentergroup.py` | `DatacenterGroup` | `Datacenter` |
| `datastoreext.py` | `DatastoreExt` | `datastoregroup.py` | `DatastoreGroup` | `Datastore` |
| `deploymentext.py` | `DeploymentExt` | `deploymentgroup.py` | `DeploymentGroup` | `Deployment` |
| `folderext.py` | `FolderExt` | `foldergroup.py` | `FolderGroup` | `Folder` |
| `guestext.py` | `GuestExt` | `guestgroup.py` | `GuestGroup` | `Guest` |
| `hostext.py` | `HostExt` | `hostgroup.py` | `HostGroup` | `Host` |
| `hvcext.py` | `HvcExt` | `hvcgroup.py` | `HvcGroup` | `Hvc` |
| `identityext.py` | `IdentityExt` | `identitygroup.py` | `IdentityGroup` | `Identity` |
| `inventoryext.py` | `InventoryExt` | `inventorygroup.py` | `InventoryGroup` | `Inventory` |
| `isoext.py` | `IsoExt` | `isogroup.py` | `IsoGroup` | `Iso` |
| `lcmext.py` | `LcmExt` | `lcmgroup.py` | `LcmGroup` | `Lcm` |
| `namespacemanagementext.py` | `NamespaceManagementExt` | `namespacemanagementgroup.py` | `NamespaceManagementGroup` | `NamespaceManagement` |
| `namespacesext.py` | `NamespacesExt` | `namespacesgroup.py` | `NamespacesGroup` | `Namespaces` |
| `networkext.py` | `NetworkExt` | `networkgroup.py` | `NetworkGroup` | `Network` |
| `ovfext.py` | `OvfExt` | `ovfgroup.py` | `OvfGroup` | `Ovf` |
| `resourcepoolext.py` | `ResourcePoolExt` | `resourcepoolgroup.py` | `ResourcePoolGroup` | `ResourcePool` |
| `servicesext.py` | `ServicesExt` | `servicesgroup.py` | `ServicesGroup` | `Services` |
| `storageext.py` | `StorageExt` | `storagegroup.py` | `StorageGroup` | `Storage` |
| `systemconfigext.py` | `SystemConfigExt` | `systemconfiggroup.py` | `SystemConfigGroup` | `SystemConfig` |
| `taggingext.py` | `TaggingExt` | `tagginggroup.py` | `TaggingGroup` | `Tagging` |
| `tokenserviceext.py` | `TokenServiceExt` | `tokenservicegroup.py` | `TokenServiceGroup` | `TokenService` |
| `topologyext.py` | `TopologyExt` | `topologygroup.py` | `TopologyGroup` | `Topology` |
| `trustedinfrastructureext.py` | `TrustedInfrastructureExt` | `trustedinfrastructuregroup.py` | `TrustedInfrastructureGroup` | `TrustedInfrastructure` |
| `vmext.py` | `VmExt` | `vmgroup.py` | `VmGroup` | `Vm` |

Counts: 30 legacy modules including `baseext.py`, mapping to 30 new modules
including `basegroup.py` (the base class which is not registered as a client
property). The remaining 29 are the public API groups exposed by `VSphereClient`.

---

## Data Model

This spec does not introduce new DTOs. Every method on every `*Group` returns a typed
DTO declared in `model/` (owned by `vsphere-data-model-and-specs`) or accepts a typed
request spec from `specs/` (also owned by that spec). When a long-running operation
is invoked, the return type is `VSphereTaskHandle` (owned by `vsphere-task-handle`).

---

## Module Layout

```
source/packages/automojo/interop/vsphere/apigroups/
├── __init__.py
├── basegroup.py
├── certificatemanagementgroup.py
├── clustergroup.py
├── computegroup.py
├── contentgroup.py
├── cryptomanagergroup.py
├── datacentergroup.py
├── datastoregroup.py
├── deploymentgroup.py
├── foldergroup.py
├── guestgroup.py
├── hostgroup.py
├── hvcgroup.py
├── identitygroup.py
├── inventorygroup.py
├── isogroup.py
├── lcmgroup.py
├── namespacemanagementgroup.py
├── namespacesgroup.py
├── networkgroup.py
├── ovfgroup.py
├── resourcepoolgroup.py
├── servicesgroup.py
├── storagegroup.py
├── systemconfiggroup.py
├── tagginggroup.py
├── tokenservicegroup.py
├── topologygroup.py
├── trustedinfrastructuregroup.py
└── vmgroup.py
```

---

## See Also

- `vsphere-client-rest-base` — registers each `*Group` as a client property.
- `vsphere-data-model-and-specs` — DTOs and request specs returned/accepted by groups.
- `vsphere-task-handle` — return type for long-running operations.
- `vsphere-vm-lifecycle-waiters`, `vsphere-content-library-deploy`,
  `vsphere-ovf-deploy`, `vsphere-guest-customization`, `vsphere-inventory-helpers`,
  `vsphere-events-stream`, `vsphere-linked-mode` — add new methods to specific groups
  beyond the mechanical migration.
- `automojo-restclient-base.restapigroup` — the parent class.

---

## Testing Strategy

1. **Structural test** — for each of the 30 legacy modules, assert the corresponding
   `*Group` module exists, exports the expected class, and that the class inherits
   `RestApiGroup`. Failure mode names the missing module by file path.

2. **API parity tests** — per `*Group`, assert each method present on the legacy
   `*Ext` class is also present on the new class. Driven by a hand-curated mapping
   table in the test module (the test does not import the legacy classes — it
   compares to a frozen snapshot of legacy public method names).

3. **Aspects forwarding tests** — for each `*Group`, sample three methods and assert
   they accept `aspects` as a keyword-only parameter with default
   `DEFAULT_VSPHERE_ASPECTS` and forward it to the underlying request.

4. **Property tests (hypothesis) — URL composition correctness:**
   - For any legal combination of `BASE_LEAF` (sampled from the 30 declared leafs),
     sub-path segments (random Unicode-safe and Unicode-unsafe strings), and query
     parameter dicts, the composed URL satisfies:
     - exactly one `/` between every adjacent segment pair (no `//`, no missing `/`)
     - URL-unsafe characters in path segments are percent-encoded
     - the URL begins with the correct root (`/api/` → API root, `/rest/` → REST root)
     - query parameters appear in alphabetical order by name
     - composing the same inputs twice produces identical output (determinism)
   - For any randomly-permuted query parameter dict input, the output is identical
     to the alphabetically-sorted variant.
   - For any `BASE_LEAF` that does not start with `/api/` or `/rest/`, group
     registration raises `SemanticError`.

5. **No-decorator audit** — a structural test scans the `apigroups/` package for any
   `@retry`-style decorator and fails the suite if one is found.

No live vCenter required for any test in this spec.
