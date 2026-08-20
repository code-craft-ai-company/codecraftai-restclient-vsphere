"""
    Tests for ContentGroup deploy methods:
    - list_items (happy / empty / tag-filtered / unknown library)
    - find_item (single / no match / multi match)
    - deploy_ovf_item (returns task handle; failure propagates)
"""


from http import HTTPStatus
from unittest.mock import MagicMock

from ccai import testbase

from ccai.credentials.basiccredential import BasicCredential

from ccai.restclient.vsphere.apigroups.inventoryerrors import (
    VSphereAmbiguousResolutionError,
    VSphereResourceNotFoundError,
)
from ccai.restclient.vsphere.model.library import LibraryItemSummary
from ccai.restclient.vsphere.specs.contentdeploy import ContentDeploySpec
from ccai.restclient.vsphere.specs.vmplacement import VmPlacementSpec
from ccai.restclient.vsphere.vsphereclient import VSphereClient
from ccai.restclient.vsphere.vspheretaskhandle import VSphereTaskHandle


def _make_client():
    cred = BasicCredential(
        identifier="vc", categories=["basic"], username="u", password="p",
    )
    client = VSphereClient(host="vc.example.com", credential=cred)
    session = MagicMock()
    client._session = session
    client._auth_token = "tok"
    return client, session


def _ok(payload):
    resp = MagicMock()
    resp.status_code = HTTPStatus.OK
    resp.json.return_value = payload
    return resp


def _status(code, payload=None):
    resp = MagicMock()
    resp.status_code = code
    resp.json.return_value = payload if payload is not None else {}
    return resp


# ----------------------------------------------------------------------
# TestListItems
# ----------------------------------------------------------------------


def test_list_items_happy() -> None:
    client, session = _make_client()
    session.get.return_value = _ok([
        {"item_id": "item-1", "library_id": "lib-1", "name": "ubuntu"},
        {"item_id": "item-2", "library_id": "lib-1", "name": "centos"},
    ])
    items = client.Content.list_items(library_id="lib-1")
    testbase.assert_equal(len(items), 2)
    testbase.assert_true(isinstance(items[0], LibraryItemSummary))
    url_arg = session.get.call_args.args[0]
    testbase.assert_equal(url_arg, "https://vc.example.com/api/content/library/item")
    return

def test_list_items_empty() -> None:
    client, session = _make_client()
    session.get.return_value = _ok([])
    items = client.Content.list_items(library_id="lib-1")
    testbase.assert_equal(items, [])
    return

def test_list_items_tag_filter() -> None:
    client, session = _make_client()
    session.get.return_value = _ok([
        {"item_id": "item-1", "library_id": "lib-1", "name": "u", "tags": ["t1"]},
        {"item_id": "item-2", "library_id": "lib-1", "name": "c", "tags": ["t2"]},
    ])
    items = client.Content.list_items(library_id="lib-1", tag="t2")
    testbase.assert_equal(len(items), 1)
    testbase.assert_equal(items[0].item_id, "item-2")
    return

def test_unknown_library_raises_not_found() -> None:
    client, session = _make_client()
    session.get.return_value = _status(HTTPStatus.NOT_FOUND)
    with testbase.raises(VSphereResourceNotFoundError):
        client.Content.list_items(library_id="lib-missing")
    return

def test_list_items_bare_string_ids() -> None:
    client, session = _make_client()
    session.get.return_value = _ok(["i-1", "i-2"])
    items = client.Content.list_items(library_id="lib-1")
    testbase.assert_equal(len(items), 2)
    testbase.assert_equal(items[0].item_id, "i-1")
    testbase.assert_equal(items[0].library_id, "lib-1")
    return


# ----------------------------------------------------------------------
# TestFindItem
# ----------------------------------------------------------------------


def test_find_item_single_match() -> None:
    client, session = _make_client()
    session.get.return_value = _ok([
        {"item_id": "i-1", "library_id": "lib-1", "name": "ubuntu"},
        {"item_id": "i-2", "library_id": "lib-1", "name": "centos"},
    ])
    item = client.Content.find_item(name="ubuntu", library_id="lib-1")
    testbase.assert_equal(item.item_id, "i-1")
    return

def test_find_item_no_match() -> None:
    client, session = _make_client()
    session.get.return_value = _ok([
        {"item_id": "i-1", "library_id": "lib-1", "name": "ubuntu"},
    ])
    with testbase.raises(VSphereResourceNotFoundError):
        client.Content.find_item(name="absent", library_id="lib-1")
    return

def test_find_item_multi_match() -> None:
    client, session = _make_client()
    # Force two libs and two matches.
    responses = [
        _ok([{"item_id": "i-1", "library_id": "lib-1", "name": "x"}]),
        _ok([{"item_id": "i-2", "library_id": "lib-2", "name": "x"}]),
    ]
    session.get.side_effect = responses
    with testbase.raises(VSphereAmbiguousResolutionError) as cm:
        client.Content.find_item(name="x", all_library_ids=["lib-1", "lib-2"])
    testbase.assert_equal(len(cm.exception.candidates), 2)
    return

def test_find_item_requires_scope() -> None:
    client, _ = _make_client()
    with testbase.raises(VSphereResourceNotFoundError):
        client.Content.find_item(name="x")
    return


# ----------------------------------------------------------------------
# TestDeployOvfItem
# ----------------------------------------------------------------------


def test_deploy_returns_task_handle() -> None:
    client, session = _make_client()
    resp = MagicMock()
    resp.status_code = HTTPStatus.OK
    resp.json.return_value = {"succeeded": True, "resource_id": "vm-new-1"}
    session.post.return_value = resp

    target = VmPlacementSpec(cluster="cluster-1", folder="folder-1", datastore="ds-1")
    deploy_spec = ContentDeploySpec(
        target_vm_name="vm-new", accept_all_eula=True, network_mappings={},
        storage_provisioning="thin",
    )
    handle = client.Content.deploy_ovf_item(
        item_id="i-1", target=target, deploy_spec=deploy_spec,
    )
    testbase.assert_true(isinstance(handle, VSphereTaskHandle))
    url_arg = session.post.call_args.args[0]
    testbase.assert_true("/api/vcenter/ovf/library-item/i-1" in url_arg)
    return

def test_deploy_http_error_raises() -> None:
    client, session = _make_client()
    resp = MagicMock()
    resp.status_code = 500
    resp.content = b"boom"
    session.post.return_value = resp

    target = VmPlacementSpec(cluster="c", folder="f", datastore="ds")
    deploy_spec = ContentDeploySpec(target_vm_name="v")
    with testbase.raises(Exception):
        client.Content.deploy_ovf_item(
            item_id="i-1", target=target, deploy_spec=deploy_spec,
        )
    return
