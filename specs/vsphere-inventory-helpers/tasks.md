# Implementation Plan — VSphere Inventory Helpers

- [x] 1. Define `VSphereResourceNotFoundError` and `VSphereAmbiguousResolutionError`
  in `apigroups/inventoryerrors.py`.

- [x] 2. Implement `InventoryGroup.find_vm_by_name(name, scope, aspects)`.

- [x] 3. Implement `InventoryGroup.find_vm_by_tag(tag, scope, aspects)`.

- [x] 4. Implement `InventoryGroup.find_datastore_with_free_gb(min_free_gb, scope,
  aspects)` with `(free_space_gb DESC, name ASC, id ASC)` selection.

- [x] 5. Implement `InventoryGroup.pick_least_loaded_host(cluster, aspects)` with
  `(load ASC, name ASC, id ASC)` selection.

- [x] 6. Document each helper's selection rule in its Sphinx docstring.

## Tests

- [x] 7. Unit tests — happy / not-found / ambiguous per helper.

- [x] 8. Property tests (hypothesis) — selection determinism:
  - `find_datastore_with_free_gb`: determinism over identical inputs; soundness;
    tie-breaker totality.
  - `pick_least_loaded_host`: determinism; soundness; tie-breaker totality.
  - `find_vm_by_name`: exact-match returns; zero matches raises
    `VSphereResourceNotFoundError`; multi-match raises
    `VSphereAmbiguousResolutionError` with all candidates.
  - `find_vm_by_tag`: result equals the subset carrying the tag, ordered by
    `(name ASC, id ASC)`.
