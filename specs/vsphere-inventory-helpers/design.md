# Design

## Overview

The inventory helpers live on `InventoryGroup` and bundle the common queries that
every consumer of the vSphere client re-invents. The helpers compose existing
`*Group` methods (`VmGroup.list`, `DatastoreGroup.list`, `HostGroup.list`, etc.)
and apply a deterministic selection rule when a single result is requested.

Selection determinism is the central design constraint: any time a helper picks one
result from a candidate set, the selection rule is a total ordering on the
candidates, documented in the helper's docstring and verified by property tests.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│   InventoryGroup helpers                                   │
│                                                            │
│   find_vm_by_name(name, scope, aspects)                    │
│   find_vm_by_tag(tag, scope, aspects)                      │
│   find_datastore_with_free_gb(min_free_gb, scope, aspects) │
│   pick_least_loaded_host(cluster, aspects)                 │
└─────────────────────┬──────────────────────────────────────┘
                      │ compose
                      ▼
┌────────────────────────────────────────────────────────────┐
│   VmGroup.list   DatastoreGroup.list   HostGroup.list      │
│   TaggingGroup.list_attached_objects                       │
└────────────────────────────────────────────────────────────┘
```

---

## Data Model

This feature does not introduce new DTOs. Errors:

```python
class VSphereResourceNotFoundError(Exception):
    """Raised when an inventory helper finds no matching resource."""


class VSphereAmbiguousResolutionError(Exception):
    """Raised when a helper that requires uniqueness finds multiple matches."""
    candidates: List[object]
```

---

## Selection Rules

| Helper | Selection rule |
| --- | --- |
| `find_vm_by_name` | name match must be unique within scope; ambiguous → raise |
| `find_vm_by_tag` | returns all matches (no selection) |
| `find_datastore_with_free_gb` | `(free_space_gb DESC, name ASC, id ASC)` → first |
| `pick_least_loaded_host` | `(load ASC, name ASC, id ASC)` → first, where `load = 0.6 * cpu_usage_percent + 0.4 * memory_usage_percent` |

---

## Module Layout

```
source/packages/ccai/restclient/vsphere/
├── apigroups/inventorygroup.py     # adds the helpers
└── apigroups/inventoryerrors.py    # VSphereResourceNotFoundError, VSphereAmbiguousResolutionError
```

---

## See Also

- `vsphere-apigroups-migration` — `InventoryGroup` parent migration.
- `vsphere-data-model-and-specs` — DTOs returned by the helpers.

---

## Testing Strategy

1. **Unit tests** — happy / not-found / ambiguous branches per helper, driven by
   fake `*Group.list` mocks.

2. **Property tests (hypothesis) — selection determinism:**
   - For any randomly-generated candidate list with arbitrary `free_space_gb`,
     `name`, `id` values, calling `find_datastore_with_free_gb` twice on the same
     input returns identical results (determinism).
   - For any candidate list, the result of `find_datastore_with_free_gb` is one of
     the inputs that satisfies the `min_free_gb` criterion (soundness).
   - For any candidate list where multiple candidates share the same
     `free_space_gb`, the result is uniquely determined by the tie-breaker
     `(name ASC, id ASC)` (total-ordering property).
   - Analogous properties for `pick_least_loaded_host`:
     - determinism over identical inputs
     - soundness (selected host is in the input cluster)
     - tie-breaker totality
   - For `find_vm_by_name`: when the input contains exactly one match, the helper
     returns it; when it contains zero matches it raises
     `VSphereResourceNotFoundError`; when it contains two or more matches it raises
     `VSphereAmbiguousResolutionError` with all matches in the `candidates` list.
   - For `find_vm_by_tag`: the result list contains exactly the inputs that carry
     the tag; ordering is by `(name ASC, id ASC)` for stability.

   Property tests use `hypothesis` strategies to generate candidate lists with
   controlled cardinality and tie patterns. No live vCenter required.
