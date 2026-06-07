# Design

## Overview

Linked Mode helpers live on `VSphereClient` itself (not on a `*Group`) because they
return either a list of metadata records or a new client instance — they are
client-shaped concerns. The helpers compose `HvcGroup` (the migrated successor of
`HvcExt`) for the underlying API and wrap the result in `LinkedVCenterRecord` DTOs.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│   VSphereClient                                            │
│   linked_vcenters(aspects) → [LinkedVCenterRecord]         │
│   for_vcenter(uuid, aspects) → VSphereClient (scoped)      │
└─────────────────────┬──────────────────────────────────────┘
                      │ delegates to
                      ▼
┌────────────────────────────────────────────────────────────┐
│   HvcGroup (migrated from HvcExt)                          │
└────────────────────────────────────────────────────────────┘
```

---

## Data Model

```python
@dataclass
class LinkedVCenterRecord:
    uuid: str
    hostname: str
    version: str
    build: str
    is_local: bool
```

---

## Module Layout

```
source/packages/ccai/restclient/vsphere/
├── vsphereclient.py              # adds linked_vcenters, for_vcenter
└── model/linkedvcenter.py        # LinkedVCenterRecord
```

---

## See Also

- `vsphere-apigroups-migration` — `HvcGroup` (the API surface).
- `vsphere-client-rest-base` — parent client.

---

## Testing Strategy

- `linked_vcenters` happy / no-linked-mode (single-entry list) / API error.
- `for_vcenter` happy / unknown uuid raises / scoped client routes correctly via
  mocked HTTP.
- No live vCenter required.
