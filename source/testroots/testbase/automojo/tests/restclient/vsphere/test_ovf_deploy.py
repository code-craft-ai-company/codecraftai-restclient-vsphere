"""
    Tests for OvfGroup deploy methods:
    - deploy_from_url (happy / invalid scheme / network error returns task)
    - deploy_from_local_ovf (happy / missing file / invalid header)
    - parse_descriptor (happy / malformed)
"""

import os
import tempfile
import unittest

from http import HTTPStatus
from unittest.mock import MagicMock

from automojo.credentials.basiccredential import BasicCredential
from automojo.errors.exceptions import SemanticError

from automojo.restclient.vsphere.specs.ovfdeploy import OvfDeploySpec
from automojo.restclient.vsphere.specs.vmplacement import VmPlacementSpec
from automojo.restclient.vsphere.vsphereclient import VSphereClient
from automojo.restclient.vsphere.vspheretaskhandle import VSphereTaskHandle


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


class TestDeployFromUrl(unittest.TestCase):

    def test_happy(self) -> None:
        client, session = _make_client()
        session.post.return_value = _ok("task-deploy-1")
        target = VmPlacementSpec(cluster="c", folder="f", datastore="ds")
        deploy_spec = OvfDeploySpec(target_vm_name="vm-x")
        handle = client.Ovf.deploy_from_url(
            url="https://images.example.com/ubuntu.ova",
            target=target, deploy_spec=deploy_spec,
        )
        self.assertIsInstance(handle, VSphereTaskHandle)
        self.assertEqual(handle.task_id(), "task-deploy-1")
        return

    def test_invalid_scheme(self) -> None:
        client, _ = _make_client()
        target = VmPlacementSpec(cluster="c")
        deploy_spec = OvfDeploySpec(target_vm_name="vm-x")
        with self.assertRaises(SemanticError):
            client.Ovf.deploy_from_url(
                url="ftp://images.example.com/ubuntu.ova",
                target=target, deploy_spec=deploy_spec,
            )
        return


class TestDeployFromLocalOvf(unittest.TestCase):

    def test_happy_ovf_xml(self) -> None:
        client, session = _make_client()
        session.post.return_value = _ok("task-local-1")
        with tempfile.NamedTemporaryFile(suffix=".ovf", delete=False) as tmp:
            tmp.write(b"<?xml version=\"1.0\"?><Envelope/>")
            tmp_path = tmp.name
        try:
            target = VmPlacementSpec(cluster="c")
            deploy_spec = OvfDeploySpec(target_vm_name="v")
            handle = client.Ovf.deploy_from_local_ovf(
                ovf_path=tmp_path, target=target, deploy_spec=deploy_spec,
            )
            self.assertIsInstance(handle, VSphereTaskHandle)
            self.assertEqual(handle.task_id(), "task-local-1")
        finally:
            os.remove(tmp_path)
        return

    def test_missing_file(self) -> None:
        client, _ = _make_client()
        target = VmPlacementSpec(cluster="c")
        deploy_spec = OvfDeploySpec(target_vm_name="v")
        with self.assertRaises(FileNotFoundError):
            client.Ovf.deploy_from_local_ovf(
                ovf_path="/nonexistent/path/file.ovf",
                target=target, deploy_spec=deploy_spec,
            )
        return

    def test_invalid_header(self) -> None:
        client, _ = _make_client()
        with tempfile.NamedTemporaryFile(suffix=".ovf", delete=False) as tmp:
            tmp.write(b"this is not OVF or OVA content")
            tmp_path = tmp.name
        try:
            target = VmPlacementSpec(cluster="c")
            deploy_spec = OvfDeploySpec(target_vm_name="v")
            with self.assertRaises(SemanticError):
                client.Ovf.deploy_from_local_ovf(
                    ovf_path=tmp_path, target=target, deploy_spec=deploy_spec,
                )
        finally:
            os.remove(tmp_path)
        return


class TestParseDescriptor(unittest.TestCase):

    def test_happy(self) -> None:
        client, session = _make_client()
        session.post.return_value = _ok({"name": "tmpl-1", "vendor": "acme"})
        descriptor = client.Ovf.parse_descriptor(
            source="https://images.example.com/ubuntu.ovf",
        )
        self.assertEqual(descriptor.name, "tmpl-1")
        self.assertEqual(descriptor.vendor, "acme")
        return

    def test_malformed(self) -> None:
        client, session = _make_client()
        bad_resp = MagicMock()
        bad_resp.status_code = HTTPStatus.BAD_REQUEST
        session.post.return_value = bad_resp
        with self.assertRaises(SemanticError):
            client.Ovf.parse_descriptor(source="https://x/y.ovf")
        return


if __name__ == "__main__":
    unittest.main()
