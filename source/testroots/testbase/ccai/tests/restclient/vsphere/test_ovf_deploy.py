"""
    Tests for OvfGroup deploy methods:
    - deploy_from_url (happy / invalid scheme / network error returns task)
    - deploy_from_local_ovf (happy / missing file / invalid header)
    - parse_descriptor (happy / malformed)
"""

import os
import tempfile

from http import HTTPStatus
from unittest.mock import MagicMock

from ccai import testbase

from ccai.credentials.basiccredential import BasicCredential
from ccai.errors.exceptions import SemanticError

from ccai.restclient.vsphere.specs.ovfdeploy import OvfDeploySpec
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


# ----------------------------------------------------------------------
# TestDeployFromUrl
# ----------------------------------------------------------------------


def test_deploy_from_url_happy() -> None:
    client, session = _make_client()
    session.post.return_value = _ok("task-deploy-1")
    target = VmPlacementSpec(cluster="c", folder="f", datastore="ds")
    deploy_spec = OvfDeploySpec(target_vm_name="vm-x")
    handle = client.Ovf.deploy_from_url(
        url="https://images.example.com/ubuntu.ova",
        target=target, deploy_spec=deploy_spec,
    )
    testbase.assert_true(isinstance(handle, VSphereTaskHandle))
    testbase.assert_equal(handle.task_id(), "task-deploy-1")
    return

def test_invalid_scheme() -> None:
    client, _ = _make_client()
    target = VmPlacementSpec(cluster="c")
    deploy_spec = OvfDeploySpec(target_vm_name="vm-x")
    with testbase.raises(SemanticError):
        client.Ovf.deploy_from_url(
            url="ftp://images.example.com/ubuntu.ova",
            target=target, deploy_spec=deploy_spec,
        )
    return


# ----------------------------------------------------------------------
# TestDeployFromLocalOvf
# ----------------------------------------------------------------------


def test_happy_ovf_xml() -> None:
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
        testbase.assert_true(isinstance(handle, VSphereTaskHandle))
        testbase.assert_equal(handle.task_id(), "task-local-1")
    finally:
        os.remove(tmp_path)
    return

def test_missing_file() -> None:
    client, _ = _make_client()
    target = VmPlacementSpec(cluster="c")
    deploy_spec = OvfDeploySpec(target_vm_name="v")
    with testbase.raises(FileNotFoundError):
        client.Ovf.deploy_from_local_ovf(
            ovf_path="/nonexistent/path/file.ovf",
            target=target, deploy_spec=deploy_spec,
        )
    return

def test_invalid_header() -> None:
    client, _ = _make_client()
    with tempfile.NamedTemporaryFile(suffix=".ovf", delete=False) as tmp:
        tmp.write(b"this is not OVF or OVA content")
        tmp_path = tmp.name
    try:
        target = VmPlacementSpec(cluster="c")
        deploy_spec = OvfDeploySpec(target_vm_name="v")
        with testbase.raises(SemanticError):
            client.Ovf.deploy_from_local_ovf(
                ovf_path=tmp_path, target=target, deploy_spec=deploy_spec,
            )
    finally:
        os.remove(tmp_path)
    return


# ----------------------------------------------------------------------
# TestParseDescriptor
# ----------------------------------------------------------------------


def test_parse_descriptor_happy() -> None:
    client, session = _make_client()
    session.post.return_value = _ok({"name": "tmpl-1", "vendor": "acme"})
    descriptor = client.Ovf.parse_descriptor(
        source="https://images.example.com/ubuntu.ovf",
    )
    testbase.assert_equal(descriptor.name, "tmpl-1")
    testbase.assert_equal(descriptor.vendor, "acme")
    return

def test_malformed() -> None:
    client, session = _make_client()
    bad_resp = MagicMock()
    bad_resp.status_code = HTTPStatus.BAD_REQUEST
    session.post.return_value = bad_resp
    with testbase.raises(SemanticError):
        client.Ovf.parse_descriptor(source="https://x/y.ovf")
    return
