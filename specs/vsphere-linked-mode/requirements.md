# Requirements

## Introduction

The `vsphere-linked-mode` feature exposes vSphere Linked Mode (Hybrid Linked Mode)
awareness on the client. The existing migrated `HvcGroup` covers the underlying
API; this feature adds the convenience helpers callers actually need: enumerating
linked vCenters and scoping subsequent operations to a specific one.

---

## Requirements

### Requirement 1: Enumerate Linked vCenters

**User Story:** As a caller, I want to enumerate the vCenters federated with the
one I am connected to.

#### Acceptance Criteria

1. WHEN `client.linked_vcenters(aspects=...)` is called THE SYSTEM SHALL return a
   list of `LinkedVCenterRecord` DTOs covering this vCenter and every federated
   peer.
2. WHEN linked mode is not configured THE SYSTEM SHALL return a single-entry list
   containing only the local vCenter.

---

### Requirement 2: Scope to a Specific vCenter

**User Story:** As a caller, I want to scope subsequent API calls to a specific
linked vCenter, so I can drive multi-vCenter workflows.

#### Acceptance Criteria

1. WHEN `client.for_vcenter(uuid=..., aspects=...)` is called with a uuid present
   in `linked_vcenters()` THE SYSTEM SHALL return a `VSphereClient` instance
   scoped to that vCenter.
2. WHEN the uuid is unknown THE SYSTEM SHALL raise
   `VSphereResourceNotFoundError`.
3. WHEN the scoped client makes a call THE SYSTEM SHALL route it to the named
   vCenter (using the HVC routing header where applicable, otherwise a separate
   session against the named vCenter).
