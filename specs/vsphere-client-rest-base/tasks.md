# Implementation Plan — VSphere Client REST Base

- [x] 1. Create the `ccai.restclient.vsphere` package skeleton (`__init__.py`,
  `apigroups/__init__.py`, `model/__init__.py`, `specs/__init__.py`,
  `enums/__init__.py`).

- [x] 2. Define `VSphereFilterState` dataclass in `vspherefilterstate.py`.

- [x] 3. Define `VSphereHealth` dataclass in `vspherehealth.py`.

- [x] 4. Define `DEFAULT_VSPHERE_ASPECTS` in `aspectsvsphere.py` (timeout=30s, no
  retry, INFO logging).

- [x] 5. Implement `VSphereClient.__init__` — validate credential type, initialise
  parent `RestClientBase`, set up empty filter state, lazy group cache dict.

- [x] 6. Implement `_authenticate()` override — POST `AUTH_LEAF`, extract `value`,
  set `vmware-api-session-id` header.

- [x] 7. Implement session renewal — register `HttpForbiddenError` /
  `HttpUnauthorizedError` in `AUTHENTICATION_FAILURES` and serialise concurrent
  renewal attempts via a per-client lock.

- [x] 8. Implement `build_api_url(leaf)` and `build_rest_url(leaf)` helpers.

- [x] 9. Implement the leaf-prefix validation hook used at API group registration.

- [x] 10. Implement the 29 API group properties as lazy-cached attributes
  (`Vm`, `Cluster`, `Compute`, `Datacenter`, `Datastore`, `Folder`, `Guest`, `Host`,
  `Inventory`, `Network`, `Ovf`, `ResourcePool`, `Services`, `Storage`, `Tagging`,
  `CertificateManagement`, `Content`, `CryptoManager`, `Deployment`, `Hvc`, `Identity`,
  `Iso`, `Lcm`, `NamespaceManagement`, `Namespaces`, `SystemConfig`, `TokenService`,
  `Topology`, `TrustedInfrastructure`).

- [x] 11. Implement `set_filter_state` / `clear_filter_state`.

- [x] 12. Implement `health(aspects=...)` — reachability + session-validity probe +
  time-skew measurement.

- [x] 13. Wire `DEFAULT_VSPHERE_ASPECTS` as the default `aspects` value on every
  public method.

## Tests

- [x] 14. Construction-validation tests (correct vs incorrect credential type, no I/O
  on construct).

- [x] 15. Authentication unit tests (success, non-2xx reclassification, header
  injection).

- [x] 16. Session renewal tests (one-shot retry on 403, single-flight serialisation,
  two-strikes propagation).

- [x] 17. URL composition tests (`/api/`, `/rest/`, invalid-prefix raises at
  registration).

- [x] 18. Property-access tests (identity, AttributeError message).

- [x] 19. Aspects forwarding tests (default applied, override forwarded).

- [x] 20. Health probe tests (unreachable, invalid-session, healthy).

- [x] 21. Filter state lifecycle tests (set, read, clear).
