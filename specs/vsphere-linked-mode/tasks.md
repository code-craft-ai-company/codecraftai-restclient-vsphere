# Implementation Plan — VSphere Linked Mode

- [x] 1. Define `LinkedVCenterRecord` in `model/linkedvcenter.py`.

- [x] 2. Implement `VSphereClient.linked_vcenters(aspects)`.

- [x] 3. Implement `VSphereClient.for_vcenter(uuid, aspects)` returning a scoped
  `VSphereClient`.

- [x] 4. Tests — `linked_vcenters` happy / no-linked-mode / API error.

- [x] 5. Tests — `for_vcenter` happy / unknown uuid raises.

- [x] 6. Tests — scoped client routes calls correctly via mocked HTTP.
