# Implementation Plan — VSphere OVF Deploy

- [x] 1. Define `OvfDeploySpec` in `specs/ovfdeploy.py`.

- [x] 2. Implement `OvfGroup.parse_descriptor(source)`.

- [x] 3. Implement `OvfGroup.deploy_from_url(url, target, deploy_spec, aspects)`.

- [x] 4. Implement `OvfGroup.deploy_from_local_ovf(path, target, deploy_spec,
  aspects)` with multipart upload.

- [x] 5. Tests — `deploy_from_url` happy / unreachable / invalid scheme.

- [x] 6. Tests — `deploy_from_local_ovf` happy / missing file / invalid header.

- [x] 7. Tests — `parse_descriptor` happy / malformed.
