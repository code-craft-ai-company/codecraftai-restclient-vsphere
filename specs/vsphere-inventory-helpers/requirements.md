# Requirements

## Introduction

The `vsphere-inventory-helpers` feature adds high-level convenience methods to
`InventoryGroup` that bundle common inventory queries used by both landscaping
coordinators and the provisioning engine. These helpers compose lower-level
`*Group` methods rather than introducing new endpoints.

Selection determinism is a hard requirement: every helper that "picks one" result
must do so by a stable, documented rule so that re-runs against an unchanged
inventory produce identical results.

---

## Requirements

### Requirement 1: Find VM by Name

#### Acceptance Criteria

1. WHEN `Inventory.find_vm_by_name(name=..., scope=None, aspects=...)` is called
   THE SYSTEM SHALL search the inventory (constrained to `scope` if provided) and
   return the matching `VirtualMachineSummary`.
2. WHEN no VM matches THE SYSTEM SHALL raise `VSphereResourceNotFoundError`.
3. WHEN multiple VMs match THE SYSTEM SHALL raise `VSphereAmbiguousResolutionError`
   listing the candidates by id and parent folder path.

---

### Requirement 2: Find VM by Tag

#### Acceptance Criteria

1. WHEN `Inventory.find_vm_by_tag(tag=..., scope=None, aspects=...)` is called THE
   SYSTEM SHALL return the list of all `VirtualMachineSummary` entries carrying
   the tag.
2. WHEN no VM carries the tag THE SYSTEM SHALL return an empty list (not raise).

---

### Requirement 3: Find Datastore With Free Capacity

#### Acceptance Criteria

1. WHEN `Inventory.find_datastore_with_free_gb(min_free_gb=..., scope=None,
   aspects=...)` is called THE SYSTEM SHALL return the `DatastoreSummary` of one
   datastore that satisfies the capacity criterion.
2. THE SYSTEM SHALL select the result deterministically: order candidates by
   `(free_space_gb DESC, name ASC, id ASC)` and return the first.
3. WHEN no datastore satisfies the criterion THE SYSTEM SHALL raise
   `VSphereResourceNotFoundError`.

---

### Requirement 4: Pick Least-Loaded Host

#### Acceptance Criteria

1. WHEN `Inventory.pick_least_loaded_host(cluster=..., aspects=...)` is called THE
   SYSTEM SHALL return the `HostSummary` of the host in `cluster` with the lowest
   load.
2. THE SYSTEM SHALL define "load" as the weighted sum
   `cpu_usage_percent * 0.6 + memory_usage_percent * 0.4`.
3. THE SYSTEM SHALL select the result deterministically: order by
   `(load ASC, name ASC, id ASC)` and return the first.
4. WHEN the cluster has no connected hosts THE SYSTEM SHALL raise
   `VSphereResourceNotFoundError`.

---

### Requirement 5: Selection Determinism

**User Story:** As a provisioning engine, I want every "pick one" helper to be
deterministic, so my `apply` is idempotent against an unchanged inventory.

#### Acceptance Criteria

1. THE SYSTEM SHALL guarantee that two invocations of any "pick one" helper
   against an unchanged inventory produce identical results.
2. THE SYSTEM SHALL guarantee that the tie-breaking rule for each helper is
   total — i.e. the result is uniquely determined even if multiple candidates
   share the primary key.
3. THE SYSTEM SHALL document the selection rule for each helper in the helper's
   Sphinx docstring.
