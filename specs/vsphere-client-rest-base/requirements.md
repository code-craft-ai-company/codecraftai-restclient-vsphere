# Requirements

## Introduction

The `vsphere-client-rest-base` feature provides the foundational `VSphereClient` class
for the `codecraftai-restclient-vsphere` package. It is the rebuilt replacement for the
legacy `codecraftai-landscaping/services/vmware/vsphere/vsphereagent.py` client, but
constructed as a `RestClientBase` subclass so it inherits Aspects-controlled
behaviour, structured logging, retry/backoff, and the shared `raise_for_http_status`
error reclassification from `codecraftai-restclient-base`.

This feature delivers only the client itself — session token mint and refresh, dual
URL roots for vSphere's `/api` and `/rest` namespaces, and the property-based access
points for the API groups. The actual API group implementations are owned by
`vsphere-apigroups-migration`. The task handle is owned by `vsphere-task-handle`.

All public methods take an `aspects: AspectsRest = DEFAULT_VSPHERE_ASPECTS` parameter.
No `@retry` decorators. Authentication failures trigger session renewal through the
existing `RestClientBase.AUTHENTICATION_FAILURES` retry hook.

---

## Requirements

### Requirement 1: Client Construction

**User Story:** As a downstream consumer (landscaping, provisioning), I want to
construct a `VSphereClient` from a base URL and a credential, so that I can begin
issuing vSphere API calls without writing transport plumbing.

#### Acceptance Criteria

1. WHEN the caller constructs `VSphereClient(base_url=..., credential=...)` with a
   `VSphereCredential` THE SYSTEM SHALL initialise the underlying `RestClientBase`
   session with the given base URL and certificate-verification settings derived from
   the credential.
2. WHEN the caller passes any other credential type THE SYSTEM SHALL raise
   `SemanticError` with a message naming the expected credential type.
3. WHEN construction succeeds THE SYSTEM SHALL NOT perform any network I/O until the
   first API call.

---

### Requirement 2: Session Authentication

**User Story:** As a downstream consumer, I want session-token authentication to
happen transparently on first use, so that I do not need to call a login method
explicitly.

#### Acceptance Criteria

1. WHEN the first API call is issued THE SYSTEM SHALL POST to `AUTH_LEAF =
   "/rest/com/vmware/cis/session"` with basic-auth headers built from the credential.
2. WHEN authentication returns 200 THE SYSTEM SHALL extract the `value` field and set
   the `vmware-api-session-id` header on the session for all subsequent requests.
3. WHEN authentication returns a non-2xx status THE SYSTEM SHALL raise a typed
   exception via `raise_for_http_status` (no silent swallow).
4. WHILE a session is held THE SYSTEM SHALL persist the session id on the
   `RestClientBase` session object so that all API groups share it.

---

### Requirement 3: Session Renewal on Failure

**User Story:** As a downstream consumer, I want session renewal to happen
automatically when vCenter expires my session, so that long-running workflows do not
fail spuriously.

#### Acceptance Criteria

1. WHEN an API call returns `HttpForbiddenError` or `HttpUnauthorizedError` THE
   SYSTEM SHALL drop the cached `vmware-api-session-id`, re-authenticate, and retry
   the call exactly once.
2. WHEN the retried call also fails with the same status THE SYSTEM SHALL let the
   exception bubble unchanged.
3. WHEN renewal is in progress THE SYSTEM SHALL serialise concurrent renewal attempts
   so that only one POST to `AUTH_LEAF` is in flight per client instance.

---

### Requirement 4: Dual URL Roots

**User Story:** As a downstream consumer, I want both the modern `/api/*` and legacy
`/rest/*` URL roots to be reachable from the same client, because vSphere genuinely
exposes both.

#### Acceptance Criteria

1. WHEN an API group declares its leaf with the `/api/` prefix THE SYSTEM SHALL
   compose the absolute URL using `build_api_url(leaf)`.
2. WHEN an API group declares its leaf with the `/rest/` prefix THE SYSTEM SHALL
   compose the absolute URL using `build_rest_url(leaf)`.
3. WHEN an API group leaf is provided without a recognised prefix THE SYSTEM SHALL
   raise `SemanticError` at API group registration time, not at call time.

---

### Requirement 5: API Group Access

**User Story:** As a downstream consumer, I want to access API groups via named
properties on the client (e.g. `client.Vm`, `client.Cluster`, `client.Inventory`),
matching the legacy `VSphereAgent` ergonomics so the rename is the only difference
callers see.

#### Acceptance Criteria

1. WHEN a caller accesses a property such as `client.Vm` THE SYSTEM SHALL return a
   `VmGroup` instance bound to this client.
2. WHEN a caller accesses the same property twice THE SYSTEM SHALL return the same
   instance (lazy, cached construction).
3. WHEN a caller accesses a property that does not map to a registered group THE
   SYSTEM SHALL raise `AttributeError` with a message listing the available groups.

---

### Requirement 6: Aspects on Every Call

**User Story:** As a downstream consumer, I want to control retry, backoff, timeout,
and logging on a per-call basis through `AspectsRest`, so that no behaviour is baked
in.

#### Acceptance Criteria

1. WHEN any API group method is called THE SYSTEM SHALL accept an `aspects:
   AspectsRest = DEFAULT_VSPHERE_ASPECTS` parameter.
2. WHEN `aspects` is omitted THE SYSTEM SHALL use `DEFAULT_VSPHERE_ASPECTS` which
   specifies a conservative timeout (30s), no retry, and structured logging at INFO.
3. WHEN `aspects` is supplied THE SYSTEM SHALL pass it through unchanged to the
   underlying `RestClientBase` request invocation.

---

### Requirement 7: Health Probe

**User Story:** As a downstream consumer, I want a small `health()` method so I can
verify the client can reach vCenter and that its session is valid before driving
larger workflows.

#### Acceptance Criteria

1. WHEN `client.health(aspects=...)` is called THE SYSTEM SHALL probe vCenter
   reachability, verify the session is valid, and return a `VSphereHealth` dataclass
   with `reachable: bool`, `session_valid: bool`, and `time_skew_seconds: float`.
2. WHEN vCenter is unreachable THE SYSTEM SHALL return `VSphereHealth(reachable=False,
   session_valid=False, time_skew_seconds=0.0)` without raising.
3. WHEN vCenter is reachable but session validation fails THE SYSTEM SHALL return
   `reachable=True, session_valid=False` without raising.

---

### Requirement 8: Filter State

**User Story:** As a downstream consumer, I want to scope subsequent operations to a
working datacenter / folder context, so that I do not have to pass identifiers into
every call.

#### Acceptance Criteria

1. WHEN `client.set_filter_state(datacenter=..., folder=...)` is called THE SYSTEM
   SHALL store these as the active `VSphereFilterState` on the client.
2. WHEN an API group method that honours filter state is called without explicit
   identifiers THE SYSTEM SHALL pass the current filter state into the underlying
   request.
3. WHEN `client.clear_filter_state()` is called THE SYSTEM SHALL reset the filter
   state to the empty/default value.
