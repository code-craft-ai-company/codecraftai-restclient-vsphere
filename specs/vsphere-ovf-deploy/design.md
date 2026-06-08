# Design

## Overview

OVF deployment methods sit on `OvfGroup`. URL-based deploy uses the vSphere
`/api/vcenter/ovf/library-item` endpoint's URL-source variant; local deploy uses
multipart upload (capability inherited from `RestApiGroup`). Both return
`VSphereTaskHandle`.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│   OvfGroup                                                 │
│   parse_descriptor(source) → OvfDescriptor                 │
│   deploy_from_url(url, target, deploy_spec, aspects)       │
│       → VSphereTaskHandle                                  │
│   deploy_from_local_ovf(path, target, deploy_spec, aspects)│
│       → VSphereTaskHandle                                  │
└────────────────────────────────────────────────────────────┘
```

---

## Data Model

```python
class OvfDeploySpec(SchemaObject):
    target_vm_name: str
    accept_all_eula: bool
    network_mappings: Dict[str, str]
    storage_provisioning: str
    annotation: Optional[str]
    additional_parameters: List[dict]
```

`OvfDescriptor` is delivered by `vsphere-data-model-and-specs`.

---

## Module Layout

```
source/packages/ccai/restclient/vsphere/
├── apigroups/ovfgroup.py     # adds parse_descriptor, deploy_from_url, deploy_from_local_ovf
└── specs/ovfdeploy.py        # OvfDeploySpec
```

---

## See Also

- `vsphere-content-library-deploy` — sibling deployment path for images already
  imported into a library.
- `vsphere-task-handle` — return type for deploy methods.

---

## Testing Strategy

- URL deploy happy / unreachable URL / invalid scheme.
- Local deploy happy / missing file / invalid OVF header.
- Descriptor parsing happy / malformed source.
- Multipart upload mocked through `MockHttpSession`.
