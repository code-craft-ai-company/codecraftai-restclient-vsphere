===================================
Code Craft AI Interop - vSphere
===================================

The ``codecraftai-restclient-vsphere`` package is a typed, aspect-driven REST client for the VMware vCenter API. It implements the ``IVPNControlPlane``-adjacent virtualization surface as a sibling to other vendor packages in the ccai suite, built on top of ``codecraftai-restclient-base``. The client replaces the legacy ``VSphereAgent`` from ``codecraftai-landscaping/services/vmware/`` — a 606-line agent class plus 29 extension modules — with a ``RestClientBase``-derived ``VSphereClient`` and 29 ``RestApiGroup`` subclasses.

This package is hand-authored against the documented vCenter REST surface and does **not** use OpenAPI code generation. The reasoning is recorded in the ``AGENTS.md`` "Codegen Decision" section and in the workspace-level ``PLAN-VPN-AND-CLOUD-PROVISIONING.md`` §9.2a.

Highlights
==========

- ``VSphereClient`` — the ``RestClientBase`` subclass that handles session-token mint, dual ``/api`` and ``/rest`` URL composition, and the 29 lazy-cached api-group properties.
- ``VSphereTaskHandle`` — implements ``ITaskHandle`` from ``codecraftai-interfaces``; sync-polling with aspects-controlled interval and timeout, injectable clock/sleeper/fetcher for test determinism.
- 29 ``apigroups/*Group`` classes covering certificate management, clusters, compute, content library, crypto manager, datacenter, datastore, deployment, folder, guest, host, hvc, identity, inventory, iso, lcm, namespace management, networks, OVF, resource pool, services, storage, system config, tagging, token service, topology, trusted infrastructure, and VMs.
- Content Library deploy (``ContentGroup.deploy_ovf_item``), OVF deploy from URL or local file (``OvfGroup.deploy_from_url`` / ``deploy_from_local_ovf``), and guest customization (Linux cloud-init + Windows sysprep renderers).
- VM lifecycle waiters: ``wait_for_power_state``, ``wait_for_tools_ready``, ``wait_for_ip_address``.
- Inventory helpers: ``find_vm_by_name``, ``find_vm_by_tag``, ``find_datastore_with_free_gb``, ``pick_least_loaded_host`` — with total tie-breaking ordering and hypothesis property-tested selection determinism.
- Events stream (``EventsGroup.stream`` with backpressure + dropped-event counting) and linked-mode helpers (``linked_vcenters``, ``for_vcenter``).

Repository Structure
====================

- ``development/`` - Runtime environment scripts.
- ``repository-setup/`` - Repository homing and setup scripts.
- ``source/packages/ccai/restclient/vsphere/`` - Package source code.
- ``source/testroots/testbase/ccai/tests/restclient/vsphere/`` - TestBase test roots.
- ``specs/`` - Requirements, design, and task documentation (Kiro-style).
- ``userguide/`` - Standards, conventions, and documentation.

Environment Setup
=================

When working in a Codex container:

.. code-block:: bash

   ./development/setup-agent-container

For local development:

.. code-block:: bash

   ./repository-setup/rehome-repository
   ./development/setup-environment

Running Tests
=============

Activate the virtual environment:

.. code-block:: bash

   source .venv/bin/activate

Run the test suite:

.. code-block:: bash

   PYTHONPATH=source/packages:source/testroots/testbase python -m pytest source/testroots -q

Standards and Conventions
=========================

- Naming conventions: ``userguide/10-02-naming-conventions.rst``
- Code organization: ``userguide/10-01-code-organization.rst``
- Coding standards: ``userguide/10-00-coding-standards.rst``

Additional Resources
====================

- User guide entry point: ``userguide/userguide.rst``
- Codegen decision: ``AGENTS.md`` (Codegen Decision section)
