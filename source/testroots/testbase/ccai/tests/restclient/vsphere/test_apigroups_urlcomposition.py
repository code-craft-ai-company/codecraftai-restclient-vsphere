"""
    URL-composition tests for the api-groups, with hypothesis-driven
    property tests covering the single-slash invariant, ordering,
    and determinism declared by the spec.
"""

import unittest

from unittest.mock import MagicMock

from ccai.testbase.properties import given
from ccai.testbase.properties import strategies as st

from ccai.credentials.basiccredential import BasicCredential
from ccai.errors.exceptions import SemanticError

from ccai.restclient.vsphere.vsphereclient import VSphereClient


_GROUP_LEAFS = [
    "/api/vcenter/datacenter",
    "/api/vcenter/cluster",
    "/api/vcenter/vm",
    "/api/vcenter/host",
    "/api/vcenter/folder",
    "/api/vcenter/network",
    "/api/vcenter/datastore",
    "/api/vcenter/iso/image",
    "/api/cis/tagging",
]


def _make_client() -> VSphereClient:
    cred = BasicCredential(
        identifier="vc-test", categories=["basic"], username="u", password="p"
    )
    rtnval = VSphereClient(host="vc.example.com", credential=cred)
    return rtnval


class TestUrlCompositionExamples(unittest.TestCase):

    def setUp(self) -> None:
        self.client = _make_client()
        return

    def test_datacenter_list_url(self) -> None:
        url = self.client.Datacenter.compose_url()
        self.assertEqual(url, "https://vc.example.com/api/vcenter/datacenter")
        return

    def test_datacenter_get_url(self) -> None:
        url = self.client.Datacenter.compose_url(parts=["dc-1"])
        self.assertEqual(url, "https://vc.example.com/api/vcenter/datacenter/dc-1")
        return

    def test_vm_list_url(self) -> None:
        url = self.client.Vm.compose_url()
        self.assertEqual(url, "https://vc.example.com/api/vcenter/vm")
        return

    def test_iso_url(self) -> None:
        url = self.client.Iso.compose_url()
        self.assertEqual(url, "https://vc.example.com/api/vcenter/iso/image")
        return

    def test_sort_params_alphabetical(self) -> None:
        raw = {"folders": ["f-1"], "datacenters": ["dc-1"]}
        sorted_params = self.client.Vm.sort_params(params=raw)
        keys = list(sorted_params.keys())
        self.assertEqual(keys, sorted(keys))
        return

    def test_unknown_prefix_rejected_at_subclass_time(self) -> None:
        from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup
        with self.assertRaises(SemanticError):
            class _Bogus(BaseGroup):
                BASE_LEAF = "/legacy/no/prefix"
        return


# ---------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------


_safe_part = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_",
    ),
    min_size=1,
    max_size=12,
)


class TestUrlCompositionProperties(unittest.TestCase):

    def setUp(self) -> None:
        self.client = _make_client()
        return

    @given(st.sampled_from(_GROUP_LEAFS), st.lists(_safe_part, min_size=0, max_size=4), constraints={"max_examples": 50})
    def test_single_slash_invariant(self, base_leaf, parts) -> None:
        # Build a synthetic group dynamically.  We can't use the cached
        # client groups because they have a fixed BASE_LEAF; instead we
        # exercise the BaseGroup.compose_url helper directly.
        from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup

        class _Synthetic(BaseGroup):
            BASE_LEAF = base_leaf

        group = _Synthetic(self.client)
        url = group.compose_url(parts=parts if len(parts) > 0 else None)
        # No accidental double slashes after the scheme separator.
        after_scheme = url.split("://", 1)[1]
        self.assertNotIn("//", after_scheme)
        # Begins with the correct host + root.
        self.assertTrue(url.startswith("https://vc.example.com" + base_leaf[:5]))
        return

    @given(st.sampled_from(_GROUP_LEAFS), st.lists(_safe_part, min_size=1, max_size=4), constraints={"max_examples": 30})
    def test_determinism(self, base_leaf, parts) -> None:
        from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup

        class _Synthetic(BaseGroup):
            BASE_LEAF = base_leaf

        group = _Synthetic(self.client)
        url1 = group.compose_url(parts=parts)
        url2 = group.compose_url(parts=parts)
        self.assertEqual(url1, url2)
        return

    @given(st.dictionaries(_safe_part, _safe_part, min_size=0, max_size=6), constraints={"max_examples": 30})
    def test_sort_params_idempotent_and_sorted(self, raw) -> None:
        from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup

        class _Synthetic(BaseGroup):
            BASE_LEAF = "/api/vcenter/vm"

        group = _Synthetic(self.client)
        first = group.sort_params(params=raw)
        again = group.sort_params(params=first)
        self.assertEqual(list(first.keys()), sorted(first.keys()))
        self.assertEqual(first, again)
        return


if __name__ == "__main__":
    unittest.main()
