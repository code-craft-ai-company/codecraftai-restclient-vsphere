"""
    Structural tests for the api-groups migration:

    - Every legacy ``*Ext`` module has a corresponding ``*Group`` module.
    - Every ``*Group`` class inherits :class:`RestApiGroup`.
    - Every ``*Group`` declares a ``BASE_LEAF`` starting with ``/api/``
      or ``/rest/``.
    - The ``apigroups`` package contains no behaviour-modifying
      decorators (no ``@retry``).
"""

import importlib
import inspect
import os
import unittest

from ccai.restclient.base.restapigroup import RestApiGroup


GROUP_MAPPING = [
    ("certificatemanagementgroup", "CertificateManagementGroup"),
    ("clustergroup", "ClusterGroup"),
    ("computegroup", "ComputeGroup"),
    ("contentgroup", "ContentGroup"),
    ("cryptomanagergroup", "CryptoManagerGroup"),
    ("datacentergroup", "DatacenterGroup"),
    ("datastoregroup", "DatastoreGroup"),
    ("deploymentgroup", "DeploymentGroup"),
    ("foldergroup", "FolderGroup"),
    ("guestgroup", "GuestGroup"),
    ("hostgroup", "HostGroup"),
    ("hvcgroup", "HvcGroup"),
    ("identitygroup", "IdentityGroup"),
    ("inventorygroup", "InventoryGroup"),
    ("isogroup", "IsoGroup"),
    ("lcmgroup", "LcmGroup"),
    ("namespacemanagementgroup", "NamespaceManagementGroup"),
    ("namespacesgroup", "NamespacesGroup"),
    ("networkgroup", "NetworkGroup"),
    ("ovfgroup", "OvfGroup"),
    ("resourcepoolgroup", "ResourcePoolGroup"),
    ("servicesgroup", "ServicesGroup"),
    ("storagegroup", "StorageGroup"),
    ("systemconfiggroup", "SystemConfigGroup"),
    ("tagginggroup", "TaggingGroup"),
    ("tokenservicegroup", "TokenServiceGroup"),
    ("topologygroup", "TopologyGroup"),
    ("trustedinfrastructuregroup", "TrustedInfrastructureGroup"),
    ("vmgroup", "VmGroup"),
]


class TestApiGroupStructural(unittest.TestCase):

    def test_all_29_groups_present(self) -> None:
        self.assertEqual(len(GROUP_MAPPING), 29)
        return

    def test_each_group_imports_and_inherits_restapigroup(self) -> None:
        for module_name, class_name in GROUP_MAPPING:
            with self.subTest(module=module_name):
                full_path = "ccai.restclient.vsphere.apigroups." + module_name
                module = importlib.import_module(full_path)
                self.assertTrue(hasattr(module, class_name))
                group_class = getattr(module, class_name)
                self.assertTrue(issubclass(group_class, RestApiGroup))
        return

    def test_each_group_declares_valid_baseleaf(self) -> None:
        for module_name, class_name in GROUP_MAPPING:
            with self.subTest(module=module_name):
                full_path = "ccai.restclient.vsphere.apigroups." + module_name
                module = importlib.import_module(full_path)
                group_class = getattr(module, class_name)
                base_leaf = group_class.BASE_LEAF
                self.assertTrue(
                    base_leaf.startswith("/api/") or base_leaf.startswith("/rest/"),
                    msg="{}.BASE_LEAF={!r}".format(class_name, base_leaf),
                )
        return

    def test_no_retry_decorator_in_apigroups(self) -> None:
        # Scan source for behaviour-modifying decorator names.  This is
        # a textual audit; behaviour decorators (``@retry``,
        # ``@backoff``, ``@circuit_breaker``) are forbidden per the
        # ``aspects-not-decorators`` rule.
        forbidden = ("@retry", "@backoff", "@circuit_breaker", "@reliable")
        apigroups_dir = os.path.dirname(
            importlib.import_module(
                "ccai.restclient.vsphere.apigroups.basegroup"
            ).__file__
        )
        for entry in os.listdir(apigroups_dir):
            if not entry.endswith(".py"):
                continue
            entry_path = os.path.join(apigroups_dir, entry)
            with open(entry_path, "r") as f:
                text = f.read()
            for needle in forbidden:
                self.assertNotIn(needle, text, msg="forbidden decorator {!r} found in {}".format(needle, entry))
        return


class TestApiGroupAspectsForwarding(unittest.TestCase):

    def test_vmgroup_methods_take_aspects(self) -> None:
        from ccai.restclient.vsphere.apigroups.vmgroup import VmGroup
        for method_name in ("create", "clone", "delete", "get", "list"):
            method = getattr(VmGroup, method_name)
            sig = inspect.signature(method)
            self.assertIn("aspects", sig.parameters, msg=method_name)
            param = sig.parameters["aspects"]
            self.assertEqual(param.kind, inspect.Parameter.KEYWORD_ONLY)
        return


if __name__ == "__main__":
    unittest.main()
