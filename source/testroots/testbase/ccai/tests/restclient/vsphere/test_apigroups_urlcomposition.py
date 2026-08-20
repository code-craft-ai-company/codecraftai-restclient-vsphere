"""
    URL-composition tests for the api-groups, with hypothesis-driven
    property tests covering the single-slash invariant, ordering,
    and determinism declared by the spec.
"""

from unittest.mock import MagicMock

from ccai import testbase

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


# ----------------------------------------------------------------------
# TestUrlCompositionExamples
# ----------------------------------------------------------------------


def test_datacenter_list_url() -> None:
    client = _make_client()
    url = client.Datacenter.compose_url()
    testbase.assert_equal(url, "https://vc.example.com/api/vcenter/datacenter")
    return


def test_datacenter_get_url() -> None:
    client = _make_client()
    url = client.Datacenter.compose_url(parts=["dc-1"])
    testbase.assert_equal(url, "https://vc.example.com/api/vcenter/datacenter/dc-1")
    return


def test_vm_list_url() -> None:
    client = _make_client()
    url = client.Vm.compose_url()
    testbase.assert_equal(url, "https://vc.example.com/api/vcenter/vm")
    return


def test_iso_url() -> None:
    client = _make_client()
    url = client.Iso.compose_url()
    testbase.assert_equal(url, "https://vc.example.com/api/vcenter/iso/image")
    return


def test_sort_params_alphabetical() -> None:
    client = _make_client()
    raw = {"folders": ["f-1"], "datacenters": ["dc-1"]}
    sorted_params = client.Vm.sort_params(params=raw)
    keys = list(sorted_params.keys())
    testbase.assert_equal(keys, sorted(keys))
    return


def test_unknown_prefix_rejected_at_subclass_time() -> None:
    from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup

    with testbase.raises(SemanticError):

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


@given(st.sampled_from(_GROUP_LEAFS), st.lists(_safe_part, min_size=0, max_size=4), constraints={"max_examples": 50})
def test_single_slash_invariant(base_leaf, parts) -> None:
    # Build a synthetic group dynamically.  We can't use the cached
    # client groups because they have a fixed BASE_LEAF; instead we
    # exercise the BaseGroup.compose_url helper directly.
    from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup

    client = _make_client()

    class _Synthetic(BaseGroup):
        BASE_LEAF = base_leaf

    group = _Synthetic(client)
    url = group.compose_url(parts=parts if len(parts) > 0 else None)
    # No accidental double slashes after the scheme separator.
    after_scheme = url.split("://", 1)[1]
    testbase.assert_true("//" not in after_scheme)
    # Begins with the correct host + root.
    testbase.assert_true(url.startswith("https://vc.example.com" + base_leaf[:5]))
    return


@given(st.sampled_from(_GROUP_LEAFS), st.lists(_safe_part, min_size=1, max_size=4), constraints={"max_examples": 30})
def test_determinism(base_leaf, parts) -> None:
    from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup

    client = _make_client()

    class _Synthetic(BaseGroup):
        BASE_LEAF = base_leaf

    group = _Synthetic(client)
    url1 = group.compose_url(parts=parts)
    url2 = group.compose_url(parts=parts)
    testbase.assert_equal(url1, url2)
    return


@given(st.dictionaries(_safe_part, _safe_part, min_size=0, max_size=6), constraints={"max_examples": 30})
def test_sort_params_idempotent_and_sorted(raw) -> None:
    from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup

    client = _make_client()

    class _Synthetic(BaseGroup):
        BASE_LEAF = "/api/vcenter/vm"

    group = _Synthetic(client)
    first = group.sort_params(params=raw)
    again = group.sort_params(params=first)
    testbase.assert_equal(list(first.keys()), sorted(first.keys()))
    testbase.assert_equal(first, again)
    return
