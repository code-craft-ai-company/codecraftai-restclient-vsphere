# Requirements

## Introduction

The `vsphere-ovf-deploy` feature adds OVF deployment methods to `OvfGroup` that
deploy a VM directly from a URL or local OVF file, bypassing the Content Library.
This is the path used for golden images that have not yet been imported into a
library.

---

## Requirements

### Requirement 1: Deploy from URL

**User Story:** As a caller, I want to deploy a VM from an HTTP(S) URL pointing
to an OVF/OVA, so I can ingest images from external image registries.

#### Acceptance Criteria

1. WHEN `Ovf.deploy_from_url(url=..., target=VmPlacementSpec(...),
   deploy_spec=OvfDeploySpec(...), aspects=...)` is called THE SYSTEM SHALL issue
   the corresponding vSphere endpoint and return a `VSphereTaskHandle`.
2. WHEN the URL is unreachable THE SYSTEM SHALL fail the task with a
   `VSphereTaskFailedError` carrying the underlying error payload.
3. WHEN the URL scheme is not `http`, `https`, or `file` THE SYSTEM SHALL raise
   `SemanticError` before issuing the request.

---

### Requirement 2: Deploy from Local OVF

**User Story:** As a caller, I want to deploy a VM from an OVF/OVA file on the
local filesystem.

#### Acceptance Criteria

1. WHEN `Ovf.deploy_from_local_ovf(path=..., target=VmPlacementSpec(...),
   deploy_spec=OvfDeploySpec(...), aspects=...)` is called THE SYSTEM SHALL upload
   the file via multipart POST and return a `VSphereTaskHandle`.
2. WHEN the file does not exist THE SYSTEM SHALL raise `FileNotFoundError`.
3. WHEN the file is not a valid OVF/OVA archive THE SYSTEM SHALL raise
   `SemanticError` after a header check, before uploading.

---

### Requirement 3: Parse OVF Descriptor

**User Story:** As a caller, I want to inspect an OVF descriptor (properties,
networks, EULA) before deploying.

#### Acceptance Criteria

1. WHEN `Ovf.parse_descriptor(source=...)` is called with a URL or local path THE
   SYSTEM SHALL return an `OvfDescriptor` DTO.
2. WHEN parsing fails THE SYSTEM SHALL raise `SemanticError` with a clear message.
