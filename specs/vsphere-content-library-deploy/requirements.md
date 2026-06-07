# Requirements

## Introduction

The `vsphere-content-library-deploy` feature wraps the vSphere Content Library API
so a VM template stored as an OVF item can be deployed directly into a target
placement. This is the path `codecraftai-provisioning` `venue-vsphere` uses for
"give me an Ubuntu 24.04 VM from the library" — the most common image-resolution
flow on private VMware infrastructure.

The feature is added as methods on `ContentGroup` (the migrated successor of
`ContentExt`).

---

## Requirements

### Requirement 1: List Library Items

**User Story:** As a caller, I want to enumerate items in a content library and
optionally filter by tag, so I can resolve an image name to a specific library
item.

#### Acceptance Criteria

1. WHEN `Content.list_items(library_id=..., tag=None, aspects=...)` is called THE
   SYSTEM SHALL return a list of `LibraryItemSummary` DTOs for that library.
2. WHEN `tag` is provided THE SYSTEM SHALL return only items carrying that tag.
3. WHEN `library_id` is unknown THE SYSTEM SHALL raise `VSphereResourceNotFoundError`.

---

### Requirement 2: Deploy OVF Item

**User Story:** As a caller, I want to deploy an OVF template from the content
library into a target placement.

#### Acceptance Criteria

1. WHEN `Content.deploy_ovf_item(item_id=..., target=VmPlacementSpec(...),
   deploy_spec=ContentDeploySpec(...), aspects=...)` is called THE SYSTEM SHALL
   issue the corresponding vSphere endpoint and return a `VSphereTaskHandle`.
2. WHEN the deployment task succeeds THE SYSTEM SHALL produce a final `TaskInfo`
   whose `target_id` is the new VM's identifier.
3. WHEN the deployment task fails THE SYSTEM SHALL propagate
   `VSphereTaskFailedError` via the task handle's `wait()`.

---

### Requirement 3: Find Item by Name or Tag

**User Story:** As a caller, I want a convenience helper that resolves a friendly
name or tag to a library item without me having to enumerate first.

#### Acceptance Criteria

1. WHEN `Content.find_item(name=..., tag=None, library_id=None, aspects=...)` is
   called THE SYSTEM SHALL search across the indicated libraries (or all
   libraries when `library_id` is omitted) and return the first matching
   `LibraryItemSummary`.
2. WHEN no match is found THE SYSTEM SHALL raise `VSphereResourceNotFoundError`.
3. WHEN multiple matches are found THE SYSTEM SHALL raise
   `VSphereAmbiguousResolutionError` listing the candidates.
