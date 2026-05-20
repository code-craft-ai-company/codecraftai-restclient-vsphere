# Design

## Overview

`VSphereClient` is a `RestClientBase` subclass that owns vSphere session-token
management and exposes the 29 API groups (delivered by `vsphere-apigroups-migration`)
as cached properties. It replaces the hand-rolled `VSphereAgent` in
`automojo-landscaping` and removes its `requests.Session` plumbing, manual session
renewal, and baked-in retry behaviour in favour of the shared infrastructure provided
by `automojo-restclient-base`.

This feature delivers only the client shell — authentication, session renewal, dual
URL composition, property-based group access, filter state, health probe, and the
default `AspectsRest` instance. The API groups themselves, the task handle, and the
data model all live in companion specs.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                       Caller / consumer                        │
│         (landscaping coordinator, provisioning venue)          │
└────────────────────────────┬───────────────────────────────────┘
                             │ constructs
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                       VSphereClient                            │
│  (subclass of automojo-restclient-base.RestClientBase)         │
│                                                                │
│   _authenticate()    ──► POST /rest/com/vmware/cis/session     │
│   build_api_url(leaf)   build_rest_url(leaf)                   │
│   set_filter_state()    clear_filter_state()                   │
│   health()                                                     │
│                                                                │
│   @property Vm        @property Cluster   @property Inventory  │
│   @property Network   @property Datastore @property Host       │
│   ... (29 groups, lazy-cached)                                 │
└────────────────────────────┬───────────────────────────────────┘
                             │ delegates to
                             ▼
┌────────────────────────────────────────────────────────────────┐
│             RestClientBase (automojo-restclient-base)          │
│   - shared HTTP session                                        │
│   - raise_for_http_status                                      │
│   - AUTHENTICATION_FAILURES hook                               │
│   - AspectsRest pipeline                                       │
└────────────────────────────────────────────────────────────────┘
```

---

## Data Model

```python
@dataclass
class VSphereHealth:
    reachable: bool
    session_valid: bool
    time_skew_seconds: float


@dataclass
class VSphereFilterState:
    datacenter: Optional[str] = None
    folder: Optional[str] = None
    cluster: Optional[str] = None
    resource_pool: Optional[str] = None
```

The default `AspectsRest` instance is named `DEFAULT_VSPHERE_ASPECTS` and lives in
`aspectsvsphere.py`. It sets a 30-second timeout, no automatic retry, and INFO-level
structured logging.

---

## Module Layout

```
source/packages/automojo/restclient/vsphere/
├── __init__.py
├── vsphereclient.py            # VSphereClient
├── vspheresession.py           # session mint/refresh helpers
├── aspectsvsphere.py           # AspectsRest defaults
├── vspherefilterstate.py       # VSphereFilterState
├── vspherehealth.py            # VSphereHealth
└── apigroups/                  # owned by vsphere-apigroups-migration
```

---

## See Also

- `vsphere-apigroups-migration` — the 29 `RestApiGroup` subclasses bound to this client.
- `vsphere-task-handle` — the `VSphereTaskHandle` returned by async-task-bearing calls.
- `vsphere-data-model-and-specs` — typed DTOs and request payloads used by groups.
- `automojo-restclient-base.restclientbase` — the parent class.
- `automojo-credentials.vspherecredential` — the credential type accepted by the
  client.

---

## Testing Strategy

Unit tests use `MockHttpSession` (the same shim used elsewhere in `automojo-interop`
REST clients) keyed on URL + method:

1. **Construction tests** — credential-type validation, no I/O on construct.
2. **Authentication tests** — verify the `AUTH_LEAF` POST, header injection of
   `vmware-api-session-id`, and reclassification of non-2xx responses.
3. **Renewal tests** — drive a sequence (200 → 403 → 200) and assert the second call
   re-authenticates exactly once; drive (200 → 403 → 403) and assert the second 403
   propagates.
4. **URL composition tests** — table-driven over `/api/`, `/rest/`, and invalid leaf
   prefixes; the invalid-prefix case must raise at group registration time.
5. **Property-based access tests** — assert two accesses to the same property return
   `is`-identical instances; assert unknown attribute access raises `AttributeError`
   with a helpful message.
6. **Aspects tests** — assert each API method accepts and forwards the supplied
   `AspectsRest`; assert the default is `DEFAULT_VSPHERE_ASPECTS`.
7. **Health tests** — three branches: unreachable, reachable-but-invalid-session, and
   fully healthy.
8. **Filter state tests** — set / read / clear cycle.

No live vCenter required for any test in this spec.
