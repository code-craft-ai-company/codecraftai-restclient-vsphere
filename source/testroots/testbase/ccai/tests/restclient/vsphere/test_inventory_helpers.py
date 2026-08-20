"""
    Tests for vsphere-inventory-helpers:
    Unit tests for happy / not-found / ambiguous branches per helper,
    plus hypothesis property tests for selection determinism, soundness,
    and tie-breaker totality.
"""


from typing import List
from unittest.mock import MagicMock

from ccai import testbase

from ccai.testbase.properties import given
from ccai.testbase.properties import strategies as st

from ccai.credentials.basiccredential import BasicCredential

from ccai.restclient.vsphere.apigroups.inventoryerrors import (
    VSphereAmbiguousResolutionError,
    VSphereResourceNotFoundError,
)
from ccai.restclient.vsphere.model.datastore import DatastoreSummary
from ccai.restclient.vsphere.model.summary import HostSummary
from ccai.restclient.vsphere.model.vm import VirtualMachineSummary
from ccai.restclient.vsphere.vsphereclient import VSphereClient


_BYTES_PER_GB = 1024 * 1024 * 1024


def _make_client():
    cred = BasicCredential(
        identifier="vc", categories=["basic"], username="u", password="p",
    )
    client = VSphereClient(host="vc.example.com", credential=cred)
    client._session = MagicMock()
    client._auth_token = "tok"
    return client


# ---------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------


# ----------------------------------------------------------------------
# TestFindVmByName
# ----------------------------------------------------------------------


def test_happy() -> None:
    client = _make_client()
    cands = [
        VirtualMachineSummary(name="vm-a", vm="vm-1"),
        VirtualMachineSummary(name="vm-b", vm="vm-2"),
    ]
    result = client.Inventory.find_vm_by_name(name="vm-a", candidates=cands)
    testbase.assert_equal(result.vm, "vm-1")
    return

def test_not_found() -> None:
    client = _make_client()
    cands = [VirtualMachineSummary(name="vm-a", vm="vm-1")]
    with testbase.raises(VSphereResourceNotFoundError):
        client.Inventory.find_vm_by_name(name="absent", candidates=cands)
    return

def test_ambiguous() -> None:
    client = _make_client()
    cands = [
        VirtualMachineSummary(name="vm-a", vm="vm-1"),
        VirtualMachineSummary(name="vm-a", vm="vm-2"),
    ]
    with testbase.raises(VSphereAmbiguousResolutionError) as cm:
        client.Inventory.find_vm_by_name(name="vm-a", candidates=cands)
    testbase.assert_equal(len(cm.exception.candidates), 2)
    return


# ----------------------------------------------------------------------
# TestFindVmByTag
# ----------------------------------------------------------------------


def test_returns_matching() -> None:
    client = _make_client()
    cands = [
        VirtualMachineSummary(name="vm-a", vm="vm-1"),
        VirtualMachineSummary(name="vm-b", vm="vm-2"),
    ]
    tag_lookup = {"vm-1": ["t1"], "vm-2": ["t2"]}
    result = client.Inventory.find_vm_by_tag(
        tag="t1", tag_lookup=tag_lookup, candidates=cands,
    )
    testbase.assert_equal(len(result), 1)
    testbase.assert_equal(result[0].vm, "vm-1")
    return

def test_no_match_returns_empty() -> None:
    client = _make_client()
    cands = [VirtualMachineSummary(name="vm-a", vm="vm-1")]
    result = client.Inventory.find_vm_by_tag(
        tag="t9", tag_lookup={"vm-1": ["t1"]}, candidates=cands,
    )
    testbase.assert_equal(result, [])
    return


# ----------------------------------------------------------------------
# TestFindDatastoreWithFreeGb
# ----------------------------------------------------------------------


def test_picks_largest_free() -> None:
    client = _make_client()
    cands = [
        DatastoreSummary(name="ds-a", datastore="ds-1",
                         free_space=10 * _BYTES_PER_GB),
        DatastoreSummary(name="ds-b", datastore="ds-2",
                         free_space=200 * _BYTES_PER_GB),
        DatastoreSummary(name="ds-c", datastore="ds-3",
                         free_space=50 * _BYTES_PER_GB),
    ]
    result = client.Inventory.find_datastore_with_free_gb(
        min_free_gb=20.0, candidates=cands,
    )
    testbase.assert_equal(result.datastore, "ds-2")
    return

def test_not_found_when_nothing_satisfies() -> None:
    client = _make_client()
    cands = [
        DatastoreSummary(name="ds-a", datastore="ds-1",
                         free_space=1 * _BYTES_PER_GB),
    ]
    with testbase.raises(VSphereResourceNotFoundError):
        client.Inventory.find_datastore_with_free_gb(
            min_free_gb=100.0, candidates=cands,
        )
    return

def test_find_datastore_tie_break_by_name_then_id() -> None:
    client = _make_client()
    cands = [
        DatastoreSummary(name="ds-b", datastore="ds-2",
                         free_space=50 * _BYTES_PER_GB),
        DatastoreSummary(name="ds-a", datastore="ds-3",
                         free_space=50 * _BYTES_PER_GB),
        DatastoreSummary(name="ds-a", datastore="ds-1",
                         free_space=50 * _BYTES_PER_GB),
    ]
    result = client.Inventory.find_datastore_with_free_gb(
        min_free_gb=10.0, candidates=cands,
    )
    # Tie on free_space; ds-a beats ds-b (name ASC); then ds-1 beats
    # ds-3 (id ASC).
    testbase.assert_equal(result.datastore, "ds-1")
    return


# ----------------------------------------------------------------------
# TestPickLeastLoadedHost
# ----------------------------------------------------------------------


def test_picks_lowest_load() -> None:
    client = _make_client()
    cands = [
        HostSummary(name="h-a", host="h-1", connection_state="CONNECTED"),
        HostSummary(name="h-b", host="h-2", connection_state="CONNECTED"),
    ]
    host_loads = {
        "h-1": {"cpu_usage_percent": 90.0, "memory_usage_percent": 80.0},
        "h-2": {"cpu_usage_percent": 10.0, "memory_usage_percent": 20.0},
    }
    result = client.Inventory.pick_least_loaded_host(
        cluster="cluster-1", host_loads=host_loads, candidates=cands,
    )
    testbase.assert_equal(result.host, "h-2")
    return

def test_no_connected_hosts_raises() -> None:
    client = _make_client()
    cands = [
        HostSummary(name="h-a", host="h-1", connection_state="DISCONNECTED"),
    ]
    with testbase.raises(VSphereResourceNotFoundError):
        client.Inventory.pick_least_loaded_host(
            cluster="cluster-1", host_loads={}, candidates=cands,
        )
    return

def test_pick_least_loaded_host_tie_break_by_name_then_id() -> None:
    client = _make_client()
    cands = [
        HostSummary(name="h-b", host="h-2"),
        HostSummary(name="h-a", host="h-4"),
        HostSummary(name="h-a", host="h-3"),
    ]
    # All loads equal (missing entries default to 0).
    result = client.Inventory.pick_least_loaded_host(
        cluster="cluster-1", host_loads={}, candidates=cands,
    )
    testbase.assert_equal(result.host, "h-3")
    return


# ---------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------


_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
    min_size=1, max_size=8,
)
_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-_"),
    min_size=1, max_size=8,
)
_free_strategy = st.integers(min_value=0, max_value=10_000)


def _ds(name: str, identifier: str, free_gb: int) -> DatastoreSummary:
    rtnval = DatastoreSummary(
        name=name, datastore=identifier, free_space=free_gb * _BYTES_PER_GB,
    )
    return rtnval


def _host(name: str, identifier: str) -> HostSummary:
    rtnval = HostSummary(name=name, host=identifier, connection_state="CONNECTED")
    return rtnval


# ----------------------------------------------------------------------
# TestDeterminismProperties
# ----------------------------------------------------------------------


@given(
    st.lists(
        st.tuples(_name_strategy, _id_strategy, _free_strategy),
        min_size=1, max_size=8,
    ),
 constraints={"max_examples": 50})
def test_find_datastore_determinism_and_soundness(triples) -> None:
    client = _make_client()
    cands = [_ds(name=n, identifier=i, free_gb=g) for (n, i, g) in triples]
    try:
        result1 = client.Inventory.find_datastore_with_free_gb(
            min_free_gb=0.0, candidates=cands,
        )
        result2 = client.Inventory.find_datastore_with_free_gb(
            min_free_gb=0.0, candidates=cands,
        )
    except VSphereResourceNotFoundError:
        return
    # Determinism: same input → same selection identity.
    testbase.assert_equal(result1.datastore, result2.datastore)
    testbase.assert_equal(result1.name, result2.name)
    # Soundness: selection is from the input set.
    names = [c.name for c in cands]
    testbase.assert_true(result1.name in names)
    return

@given(st.lists(st.tuples(_name_strategy, _id_strategy), min_size=1, max_size=8), constraints={"max_examples": 50})
def test_find_datastore_tie_breaker_totality(pairs) -> None:
    client = _make_client()
    # All same free space — tie-break by name then id.
    cands = [_ds(name=n, identifier=i, free_gb=50) for (n, i) in pairs]
    result1 = client.Inventory.find_datastore_with_free_gb(
        min_free_gb=0.0, candidates=cands,
    )
    # Expected: min by (name ASC, id ASC).
    expected = sorted(cands, key=lambda r: (r.name, r.datastore))[0]
    testbase.assert_equal(result1.name, expected.name)
    testbase.assert_equal(result1.datastore, expected.datastore)
    return

@given(st.lists(st.tuples(_name_strategy, _id_strategy), min_size=1, max_size=8), constraints={"max_examples": 50})
def test_pick_host_tie_breaker_totality(pairs) -> None:
    client = _make_client()
    cands = [_host(name=n, identifier=i) for (n, i) in pairs]
    result = client.Inventory.pick_least_loaded_host(
        cluster="c", host_loads={}, candidates=cands,
    )
    expected = sorted(cands, key=lambda r: (r.name, r.host))[0]
    testbase.assert_equal(result.name, expected.name)
    testbase.assert_equal(result.host, expected.host)
    return

@given(st.lists(st.tuples(_name_strategy, _id_strategy), min_size=0, max_size=8), constraints={"max_examples": 50})
def test_find_vm_by_tag_ordering(pairs) -> None:
    client = _make_client()
    vms = [
        VirtualMachineSummary(name=n, vm=i) for (n, i) in pairs
    ]
    tag_lookup = {v.vm: ["t1"] for v in vms}
    result = client.Inventory.find_vm_by_tag(
        tag="t1", tag_lookup=tag_lookup, candidates=vms,
    )
    # Stable ordering by (name ASC, vm ASC).
    names_and_ids = [(v.name, v.vm) for v in result]
    testbase.assert_equal(names_and_ids, sorted(names_and_ids))
    return

@given(_name_strategy, st.lists(_id_strategy, min_size=0, max_size=5), constraints={"max_examples": 50})
def test_find_vm_by_name_branch_behaviour(target_name, extra_ids) -> None:
    client = _make_client()
    vms = [
        VirtualMachineSummary(name=target_name, vm=identifier)
        for identifier in extra_ids
    ]
    if len(vms) == 0:
        with testbase.raises(VSphereResourceNotFoundError):
            client.Inventory.find_vm_by_name(name=target_name, candidates=vms)
    elif len(vms) == 1:
        result = client.Inventory.find_vm_by_name(
            name=target_name, candidates=vms,
        )
        testbase.assert_equal(result.vm, vms[0].vm)
    else:
        with testbase.raises(VSphereAmbiguousResolutionError) as cm:
            client.Inventory.find_vm_by_name(name=target_name, candidates=vms)
        testbase.assert_equal(len(cm.exception.candidates), len(vms))
    return
