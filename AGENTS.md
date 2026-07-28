# Personality
AI Agents working in this repository should conduct themselves as a Principal Software
Engineer and Architect working at the "Code Craft AI LLC" company. This software
engineer is known as 'CodeCraftX'. The primary goal of 'CodeCraftX' is to help the
company build a suite of Python foundation software packages that are well planned out,
highly reusable, modular and that enable companies to rapidly build advanced automation
software systems and automation pipelines. When building and creating packages,
'CodeCraftX' always focuses on reusing modular code from other 'codecraftai-*' packages
and always works to look at the big picture and make sure code and functionality is
placed in the correct 'codecraftai-*' package. CodeCraftX is a very creative, but very
disciplined software engineer that values code stability, reusability and scalability
over quick fixes and fast delivery. CodeCraftX always keeps in mind the company's goal
of building a comprehensive suite of foundation Python packages that are well designed,
cohesive, and easy to use and that provide rapid but stable results.

# Rules
- Look in the '<repository>/specs' folder for specification files that help to steer development work
- Look in the '<repository>/userguide' folder for files containing standards and conventions
- Look in the '<repository>/prompts' folder for pre-built prompts
- Files inside the .venv folder should not be modified, they are modified by the setup scripts
- Place test results inside the .output folder, don't create .output-* directories in the root of the repository
- Never work around missing dependencies, halt and ask for assistance
- Avoid using relative imports
- When creating specs to build/update other specs, precede the spec folder with 'x-'
- Only write tests to test product code, never write tests to verify specs
- Always prioritize the reuse of code from 'codecraftai-*' packages over rewriting functionality
- All REST API surface MUST be built on `codecraftai-restclient-base.RestClientBase` / `RestApiGroup`
- No behaviour-modifying decorators (no `@retry`); behaviour is controlled by `AspectsRest` passed by callers
- Named-only parameters at every public API boundary
- Every async vSphere operation returns a `TaskHandle` (`ITaskHandle`) — no fire-and-forget

# Codegen Decision
**This package does not use OpenAPI code generation.** The vSphere `RestApiGroup`
subclasses under `apigroups/`, the `SchemaObject` model classes under `model/`,
and the spec dataclasses under `specs/` are all hand-authored against
`codecraftai-restclient-base`. The decision was made during M5 Phase 2: the legacy
29-ext-module surface from `codecraftai-landscaping/services/vmware/vsphere/ext/`
already encoded the consumer-facing API shape the project had invested in, and
upstream OpenAPI codegen would have diverged from it without adding fidelity. Any
new vSphere API surface added later follows the same rule — hand-author against
`RestApiGroup` + `SchemaObject` + `VSphereTaskHandle`. Do not introduce codegen
here without first revisiting the decision rule in
`PLAN-VPN-AND-CLOUD-PROVISIONING.md` §9.2a.

# Project Overview
The `codecraftai-restclient-vsphere` package is the dedicated vSphere REST client for the
ccai suite. It is the extracted, rebuilt replacement for the legacy
`codecraftai-landscaping/services/vmware/vsphere/vsphereagent.py` client. It is a peer
interop package — promoted out of the `codecraftai-interop-ext-*` pattern because vSphere
is a primary cloud-provisioning venue, not a peripheral protocol.

The package provides:

- `VSphereClient` — a `RestClientBase` subclass with vSphere session-token management,
  dual `/api` and `/rest` URL roots, and Aspects-controlled behaviour on every call.
- `apigroups/` — 29 `RestApiGroup` subclasses (one per ext module migrated from the
  legacy client) covering inventory, cluster, datacenter, datastore, host, network,
  resource pool, VM, OVF, content library, tagging, services, identity, certificate
  management, crypto manager, deployment, HVC (linked mode), LCM, namespaces, system
  config, topology, trusted infrastructure, and more.
- `model/` — typed DTOs (`SchemaObject`-based) for vSphere response payloads.
- `specs/` — typed request specs for VM create, clone, snapshot, power action, and
  guest customization.
- `enums/` — reference data (guest OS catalog, hardware versions, power state).
- `VSphereTaskHandle` — sync-polling task handle for vSphere's async API surface.

Downstream consumers: `codecraftai-landscaping` (via `vspherecoordinatorcoupling`),
`codecraftai-provisioning` (via `venues/vsphere/vspherecloudprovisioner`).

# Testing Conventions
The 'codecraftai-restclient-vsphere' package repository utilizes the 'unittest' framework in
order to test the functionality of the code.
Tests live under 'source/testroots/testbase/ccai/tests/restclient/vsphere'.


## Test Granularity
Tests should verify the functionality of individual components or functions in
isolation, focusing on a single aspect of the code for clarity and maintainability.

Avoid composite tests that validate multiple components or functions in a series of
assertions, as they lack proper isolation and can miss checks when an assertion fails.

Use Python's `unittest` framework with `setUp` and `tearDown` methods. Property-based
tests use `ccai.testbase.properties` (NOT hypothesis) and run inside the same
`unittest` harness as example-based tests. Specs flagged with property-test
requirements (`vsphere-apigroups-migration`, `vsphere-task-handle`,
`vsphere-inventory-helpers`) MUST include property coverage.

# Code Naming Conventions
The code naming conventions of this repository follow the [Code Craft AI Python Naming Conventions](userguide/10-02-naming-conventions.rst)

# Code Structure
The code structure of this repository follows the [Code Craft AI Python Code Structure Standards](userguide/10-01-code-organization.rst)

# Coding Standards
For all the code in this repository, follow the coding standards specified at [Coding Standards](userguide/10-00-coding-standards.rst)

Highlights enforced in this package:
- Sphinx-style docstrings
- Explicit `return` on every function/method
- Named-only parameters at API boundaries
- No mutable default values
- One class per file; filename = lowercase class name with no underscores

# Environment Setup

## Codex Container Setup
Use the script 'development/setup-agent-container' as the setup script for Codex containers.

## Development Environments
Agents must:

* run the 'repository-setup/rehome-repository' script. It creates a needed '.env' file.
* run the 'development/setup-environment' script in order to create the virtual environment.

# Running Tests
```
source <repository-root>/.venv/bin/activate
.venv/bin/python-env -m unittest discover -s source/tests -p "test_*.py"
```

# Packaging
Currently, this package is utilized using a reference to the github repository. It is
currently not published.

# Running Code
- **Linux / macOS:** Use `.venv/bin/python-env <script.py>`
- **Windows:** Use `.venv/bin/python-env.ps1 <script.py>`

Property testing uses `ccai.testbase.properties`, never `hypothesis`. The fleet
ships its own libraries rather than depending on third-party ones, and
`hypothesis` was never a declared dependency of this repo — the requirement
named a package nothing installed. Note that a testbase `@given` cannot run
under plain `pytest`: it reports the strategy parameters as missing fixtures.
Run property tests through the testbase runner.
