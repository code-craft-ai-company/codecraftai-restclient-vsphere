# Implementation Plan — VSphere Content Library Deploy

- [x] 1. Define `LibraryItemSummary` in `model/library.py`.

- [x] 2. Define `ContentDeploySpec` in `specs/contentdeploy.py`.

- [x] 3. Implement `ContentGroup.list_items(library_id, tag, aspects)`.

- [x] 4. Implement `ContentGroup.find_item(name, tag, library_id, aspects)`.

- [x] 5. Implement `ContentGroup.deploy_ovf_item(item_id, target, deploy_spec,
  aspects)` returning a `VSphereTaskHandle`.

- [x] 6. Tests — `list_items` happy, empty, tag-filtered, unknown library.

- [x] 7. Tests — `find_item` single, no match, multi match.

- [x] 8. Tests — `deploy_ovf_item` returns task handle; wait converges to success;
  failure propagates `VSphereTaskFailedError`.
