# Design

## Overview

Guest customization is the vCenter-driven injection of hostname, network
configuration, DNS, SSH keys, and first-boot commands into a freshly-deployed VM.
The feature renders the `VmGuestCustomizationSpec` (declared in
`vsphere-data-model-and-specs`) into one of two backend payloads — cloud-init for
Linux guests, sysprep unattend.xml for Windows guests — and submits the resulting
spec to the vCenter customization endpoint.

The rendering logic lives in this package; vCenter is responsible for delivering
the payload to the VM via the standard guest-customization framework.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│   GuestGroup.apply_guest_customization_spec                │
│       (vm, spec, aspects) → VSphereTaskHandle              │
└─────────────────────┬──────────────────────────────────────┘
                      │ branches on detected guest OS family
                      ▼
┌────────────────────────────────────────────────────────────┐
│   LinuxCloudInitRenderer    WindowsSysprepRenderer         │
│   - render(spec) → str      - render(spec) → str           │
└────────────────────────────────────────────────────────────┘
```

---

## Data Model

`VmGuestCustomizationSpec` is owned by `vsphere-data-model-and-specs`. Composed
nested type used by this feature:

```python
class NetworkMode(Enum):
    DHCP = "DHCP"
    STATIC = "STATIC"


@dataclass
class NetworkConfig:
    nic_index: int
    mode: NetworkMode
    ipv4_address: Optional[str]
    ipv4_prefix: Optional[int]
    ipv4_gateway: Optional[str]
    ipv6_address: Optional[str]
    ipv6_prefix: Optional[int]
    ipv6_gateway: Optional[str]
```

---

## Module Layout

```
source/packages/automojo/restclient/vsphere/
├── apigroups/guestgroup.py            # adds apply_guest_customization_spec
└── apigroups/customizationrenderers.py  # LinuxCloudInitRenderer, WindowsSysprepRenderer
```

---

## See Also

- `vsphere-data-model-and-specs` — `VmGuestCustomizationSpec`.
- `vsphere-task-handle` — return type.
- `automojo-provisioning` `cloud-init-injection` — sibling helper that builds the
  cloud-init blocks the renderer accepts.

---

## Testing Strategy

- Rendering tests — example specs → expected cloud-init / sysprep XML; golden-file
  comparison.
- Validation tests — hostname rules, network mode/address consistency, ssh-keys on
  Windows raises.
- Task-handle return shape verified via mocked HTTP.
- No live vCenter required.
