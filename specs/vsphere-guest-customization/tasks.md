# Implementation Plan — VSphere Guest Customization

- [x] 1. Define `NetworkMode` and `NetworkConfig` (composed by
  `VmGuestCustomizationSpec`).

- [x] 2. Implement `LinuxCloudInitRenderer.render(spec) -> str`.

- [x] 3. Implement `WindowsSysprepRenderer.render(spec) -> str`.

- [x] 4. Implement `GuestGroup.apply_guest_customization_spec(vm, spec, aspects)`:
  - detect guest OS family
  - dispatch to the right renderer
  - submit to vCenter; return `VSphereTaskHandle`

- [x] 5. Validation: hostname DNS-label rules.

- [x] 6. Validation: network mode / address-field consistency.

- [x] 7. Validation: SSH keys on Windows raises.

- [x] 8. Tests — Linux renderer golden file.

- [x] 9. Tests — Windows renderer golden file.

- [x] 10. Tests — validation rejections.

- [x] 11. Tests — unknown guest OS family raises `SemanticError`.

- [x] 12. Tests — task-handle return shape.
