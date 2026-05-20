"""
    Tests for the vsphere-linked-mode feature:
    - VSphereClient.linked_vcenters happy / not-configured / API error
    - VSphereClient.for_vcenter happy / unknown uuid raises
    - Scoped client routes to the named host
"""

import unittest

from http import HTTPStatus
from unittest.mock import MagicMock

from automojo.credentials.basiccredential import BasicCredential

from automojo.restclient.vsphere.apigroups.inventoryerrors import (
    VSphereResourceNotFoundError,
)
from automojo.restclient.vsphere.model.linkedvcenter import LinkedVCenterRecord
from automojo.restclient.vsphere.vsphereclient import VSphereClient


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


class TestLinkedVcenters(unittest.TestCase):

    def test_happy_multi_peer(self) -> None:
        client = _make_client()
        client._session.get.return_value = _ok([
            {"uuid": "uuid-local", "hostname": "vc.example.com",
             "is_local": True, "version": "8.0"},
            {"uuid": "uuid-peer", "hostname": "vc-peer.example.com",
             "is_local": False, "version": "8.0"},
        ])
        result = client.linked_vcenters()
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], LinkedVCenterRecord)
        return

    def test_not_configured_returns_local_only(self) -> None:
        client = _make_client()
        resp = MagicMock()
        resp.status_code = HTTPStatus.NOT_FOUND
        client._session.get.return_value = resp
        result = client.linked_vcenters()
        self.assertEqual(len(result), 1)
        self.assertTrue(bool(result[0].is_local))
        return

    def test_empty_list_returns_local_only(self) -> None:
        client = _make_client()
        client._session.get.return_value = _ok([])
        result = client.linked_vcenters()
        self.assertEqual(len(result), 1)
        return


class TestForVcenter(unittest.TestCase):

    def test_returns_local_when_uuid_local(self) -> None:
        client = _make_client()
        client._session.get.return_value = _ok([
            {"uuid": "uuid-local", "hostname": "vc.example.com", "is_local": True},
            {"uuid": "uuid-peer", "hostname": "vc-peer.example.com", "is_local": False},
        ])
        scoped = client.for_vcenter(uuid="uuid-local")
        self.assertIs(scoped, client)
        return

    def test_returns_new_client_for_peer(self) -> None:
        client = _make_client()
        client._session.get.return_value = _ok([
            {"uuid": "uuid-local", "hostname": "vc.example.com", "is_local": True},
            {"uuid": "uuid-peer", "hostname": "vc-peer.example.com", "is_local": False},
        ])
        scoped = client.for_vcenter(uuid="uuid-peer")
        self.assertIsInstance(scoped, VSphereClient)
        self.assertIsNot(scoped, client)
        self.assertEqual(scoped._host, "vc-peer.example.com")
        return

    def test_unknown_uuid_raises(self) -> None:
        client = _make_client()
        client._session.get.return_value = _ok([
            {"uuid": "uuid-local", "hostname": "vc.example.com", "is_local": True},
        ])
        with self.assertRaises(VSphereResourceNotFoundError):
            client.for_vcenter(uuid="uuid-absent")
        return


if __name__ == "__main__":
    unittest.main()
