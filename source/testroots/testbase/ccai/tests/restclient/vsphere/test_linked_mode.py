"""
    Tests for the vsphere-linked-mode feature:
    - VSphereClient.linked_vcenters happy / not-configured / API error
    - VSphereClient.for_vcenter happy / unknown uuid raises
    - Scoped client routes to the named host
"""


from http import HTTPStatus
from unittest.mock import MagicMock

from ccai import testbase

from ccai.credentials.basiccredential import BasicCredential

from ccai.restclient.vsphere.apigroups.inventoryerrors import (
    VSphereResourceNotFoundError,
)
from ccai.restclient.vsphere.model.linkedvcenter import LinkedVCenterRecord
from ccai.restclient.vsphere.vsphereclient import VSphereClient


def _make_client(host: str = "vc.example.com") -> VSphereClient:
    cred = BasicCredential(
        identifier="vc", categories=["basic"], username="u", password="p",
    )
    client = VSphereClient(host=host, credential=cred)
    client._session = MagicMock()
    client._auth_token = "tok"
    return client


def _ok(payload):
    resp = MagicMock()
    resp.status_code = HTTPStatus.OK
    resp.json.return_value = payload
    return resp


# ----------------------------------------------------------------------
# TestLinkedVcenters
# ----------------------------------------------------------------------


def test_happy_multi_peer() -> None:
    client = _make_client()
    client._session.get.return_value = _ok([
        {"uuid": "uuid-local", "hostname": "vc.example.com",
         "is_local": True, "version": "8.0"},
        {"uuid": "uuid-peer", "hostname": "vc-peer.example.com",
         "is_local": False, "version": "8.0"},
    ])
    result = client.linked_vcenters()
    testbase.assert_equal(len(result), 2)
    testbase.assert_true(isinstance(result[0], LinkedVCenterRecord))
    return

def test_not_configured_returns_local_only() -> None:
    client = _make_client()
    resp = MagicMock()
    resp.status_code = HTTPStatus.NOT_FOUND
    client._session.get.return_value = resp
    result = client.linked_vcenters()
    testbase.assert_equal(len(result), 1)
    testbase.assert_true(bool(result[0].is_local))
    return

def test_empty_list_returns_local_only() -> None:
    client = _make_client()
    client._session.get.return_value = _ok([])
    result = client.linked_vcenters()
    testbase.assert_equal(len(result), 1)
    return


# ----------------------------------------------------------------------
# TestForVcenter
# ----------------------------------------------------------------------


def test_returns_local_when_uuid_local() -> None:
    client = _make_client()
    client._session.get.return_value = _ok([
        {"uuid": "uuid-local", "hostname": "vc.example.com", "is_local": True},
        {"uuid": "uuid-peer", "hostname": "vc-peer.example.com", "is_local": False},
    ])
    scoped = client.for_vcenter(uuid="uuid-local")
    testbase.assert_true(scoped is client)
    return

def test_returns_new_client_for_peer() -> None:
    client = _make_client()
    client._session.get.return_value = _ok([
        {"uuid": "uuid-local", "hostname": "vc.example.com", "is_local": True},
        {"uuid": "uuid-peer", "hostname": "vc-peer.example.com", "is_local": False},
    ])
    scoped = client.for_vcenter(uuid="uuid-peer")
    testbase.assert_true(isinstance(scoped, VSphereClient))
    testbase.assert_true(scoped is not client)
    testbase.assert_equal(scoped._host, "vc-peer.example.com")
    return

def test_unknown_uuid_raises() -> None:
    client = _make_client()
    client._session.get.return_value = _ok([
        {"uuid": "uuid-local", "hostname": "vc.example.com", "is_local": True},
    ])
    with testbase.raises(VSphereResourceNotFoundError):
        client.for_vcenter(uuid="uuid-absent")
    return
