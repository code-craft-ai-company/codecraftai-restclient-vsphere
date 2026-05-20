# Requirements

## Introduction

The `vsphere-apigroups-migration` feature migrates the 29 `*Ext` extension classes
from `automojo-landscaping/source/packages/automojo/landscaping/services/vmware/vsphere/ext/`
into a new `apigroups/` package under `automojo-restclient-vsphere`, rebuilt as
`RestApiGroup` subclasses.

This is a structural and naming migration, not a semantic rewrite — the goal is for
each `*Group` class to expose the same logical API surface as the corresponding `*Ext`
class while inheriting `RestApiGroup` behaviour for URL composition, Aspects, and
response handling. New capabilities (waiters, content library deploy, OVF deploy,
guest customization, etc.) are owned by separate specs in the same package.

The migration is exhaustive: all 29 ext modules MUST be migrated; none may be left
behind. A property-test suite verifies URL composition correctness across the full
mapping.

---

## Requirements

### Requirement 1: Class Migration Mapping

**User Story:** As a downstream consumer, I want a deterministic name mapping from
the legacy `*Ext` classes to the new `*Group` classes, so I can update import sites
mechanically.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide one `*Group` class per legacy `*Ext` class, named by
   stripping the `Ext` suffix and appending `Group` (e.g. `VmExt → VmGroup`).
2. THE SYSTEM SHALL place each `*Group` class in a module named after the class in
   all lowercase with no underscores (e.g. `vmgroup.py`).
3. THE SYSTEM SHALL register each `*Group` as a property on `VSphereClient` whose
   name matches the legacy `VSphereAgent` property name (e.g. `client.Vm`).

---

### Requirement 2: RestApiGroup Inheritance

**User Story:** As a downstream consumer, I want every API group to inherit
`RestApiGroup` behaviour, so URL composition, Aspects handling, content-type
negotiation, and response paging come from a single audited source.

#### Acceptance Criteria

1. WHEN any `*Group` class is loaded THE SYSTEM SHALL verify it inherits from
   `automojo.restclient.base.restapigroup.RestApiGroup`.
2. WHEN any `*Group` class declares a `BASE_LEAF` THE SYSTEM SHALL ensure the leaf
   begins with either `/api/` or `/rest/` to select the corresponding URL root.
3. WHEN a `*Group` class composes a sub-path THE SYSTEM SHALL do so via the
   `RestApiGroup` URL composition helpers (no manual string concatenation).

---

### Requirement 3: URL Composition Correctness

**User Story:** As a downstream consumer, I want absolute URLs constructed by every
`*Group` to be correct under all valid input combinations, so I never trip on a
malformed URL in production.

#### Acceptance Criteria

1. WHEN a `*Group` composes a URL from a `BASE_LEAF` and a sub-path THE SYSTEM SHALL
   produce a single-slash-separated absolute URL (no `//`, no missing `/`).
2. WHEN any path component contains URL-unsafe characters THE SYSTEM SHALL
   percent-encode them via the `RestApiGroup` helpers.
3. WHEN multiple sub-path segments are joined THE SYSTEM SHALL preserve their order.
4. WHERE a `*Group` accepts query parameters THE SYSTEM SHALL emit them in
   deterministic order, sorted by parameter name.

---

### Requirement 4: Aspects on Every Method

**User Story:** As a downstream consumer, I want every method on every `*Group` to
take an `aspects: AspectsRest = DEFAULT_VSPHERE_ASPECTS` parameter, so behaviour is
caller-controlled.

#### Acceptance Criteria

1. WHEN any public method is declared on a `*Group` class THE SYSTEM SHALL include
   an `aspects` keyword-only parameter with default `DEFAULT_VSPHERE_ASPECTS`.
2. WHEN that method invokes the underlying request THE SYSTEM SHALL pass `aspects`
   through to `RestApiGroup.request(...)`.
3. THE SYSTEM SHALL NOT use any behaviour-modifying decorator (e.g. `@retry`) on any
   `*Group` method.

---

### Requirement 5: API Surface Parity with Legacy Ext Classes

**User Story:** As a downstream consumer of the legacy `*Ext` classes, I want each
new `*Group` class to expose at minimum the methods the legacy class exposed, so my
migration is purely a rename.

#### Acceptance Criteria

1. WHEN the migration is complete THE SYSTEM SHALL provide at least one method on
   each `*Group` for every public method on the corresponding legacy `*Ext` class.
2. WHEN a legacy method's signature used positional parameters THE SYSTEM SHALL
   convert them to keyword-only parameters in the new method.
3. WHEN a legacy method returned a raw dict or `requests.Response` THE SYSTEM SHALL
   return a typed DTO from `model/` (owned by `vsphere-data-model-and-specs`) instead.

---

### Requirement 6: Long-Running Operations Return TaskHandle

**User Story:** As a downstream consumer, I want every long-running vSphere operation
to return a `VSphereTaskHandle` so I can poll for completion through a uniform
interface.

#### Acceptance Criteria

1. WHEN a `*Group` method invokes a vSphere endpoint that returns a task id THE
   SYSTEM SHALL return a `VSphereTaskHandle` (per `vsphere-task-handle`).
2. WHEN a `*Group` method invokes a synchronous endpoint THE SYSTEM SHALL return the
   appropriate typed DTO directly (never wrap in a task handle).
3. WHEN the underlying endpoint can be either sync or async depending on parameters
   THE SYSTEM SHALL provide two distinct methods, not a single union-returning
   method.

---

### Requirement 7: Migration Completeness

**User Story:** As a downstream consumer, I want assurance that all 29 ext modules
were migrated, so I am not surprised by a missing capability.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide all 29 `*Group` modules enumerated in the design's
   migration mapping table.
2. THE SYSTEM SHALL include an automated structural test that asserts each expected
   `*Group` module exists, exports the expected class, and that the class inherits
   `RestApiGroup`.
3. WHEN a new `*Group` is added in the future THE SYSTEM SHALL require the
   structural test to be updated in the same change.
