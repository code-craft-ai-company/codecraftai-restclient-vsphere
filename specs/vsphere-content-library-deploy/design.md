# Design

## Overview

The content-library deploy methods sit on the migrated `ContentGroup` class. They
wrap the `/api/content/library/item` and `/api/vcenter/ovf/library-item`
endpoints. Deployment is an async task — every deploy entry point returns a
`VSphereTaskHandle`.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│   ContentGroup (migrated from ContentExt)                  │
│                                                            │
│   list_items(library_id, tag, aspects) → [LibraryItemSummary]
│   find_item(name, tag, library_id, aspects) → LibraryItemSummary
│   deploy_ovf_item(item_id, target, deploy_spec, aspects)   │
│       → VSphereTaskHandle                                  │
└─────────────────────┬──────────────────────────────────────┘
                      │ uses
                      ▼
┌────────────────────────────────────────────────────────────┐
│   TaggingGroup.list_attached_objects (for tag resolution)  │
└────────────────────────────────────────────────────────────┘
```

---

## Data Model

```python
@dataclass
class LibraryItemSummary:
    item_id: str
    library_id: str
    name: str
    type: str            # "ovf", "iso", "vm-template", ...
    description: Optional[str]
    creation_time: datetime
    tags: List[str]


class ContentDeploySpec(SchemaObject):
    target_vm_name: str
    accept_all_eula: bool
    network_mappings: Dict[str, str]      # ovf network name → portgroup id
    storage_provisioning: str             # "thin" | "thick" | "eagerZeroedThick"
    additional_parameters: List[dict]
```

---

## Module Layout

```
source/packages/ccai/restclient/vsphere/
├── apigroups/contentgroup.py     # adds list_items, find_item, deploy_ovf_item
├── model/library.py              # LibraryItemSummary
└── specs/contentdeploy.py        # ContentDeploySpec
```

---

## See Also

- `vsphere-apigroups-migration` — `ContentGroup` migration parent.
- `vsphere-task-handle` — return type for `deploy_ovf_item`.
- `vsphere-data-model-and-specs` — `VmPlacementSpec` used as target.
- `vsphere-ovf-deploy` — sibling spec for deploying OVF from URL/local path
  (i.e. images that are not yet in the library).

---

## Testing Strategy

- `list_items` happy / empty / tag-filtered / unknown library.
- `find_item` single-match / no-match raises / multi-match raises.
- `deploy_ovf_item` happy returns task handle; task wait converges to success;
  failed deploy raises `VSphereTaskFailedError`.
- Mock HTTP throughout; no live vCenter.
