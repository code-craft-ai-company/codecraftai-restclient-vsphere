"""
    Behavioural tests for a sample of api-group methods, verifying URL
    composition, parameter sorting, and DTO parsing using mocked
    sessions.
"""

from http import HTTPStatus
from unittest.mock import MagicMock

from ccai import testbase

from ccai.credentials.basiccredential import BasicCredential

from ccai.restclient.vsphere.model.summary import DatacenterSummary
from ccai.restclient.vsphere.vsphereclient import VSphereClient


def _make_client_with_fake_session():
    cred = BasicCredential(identifier="vc", categories=["basic"], username="u", password="p")
    client = VSphereClient(host="vc.example.com", credential=cred)

    fake_session = MagicMock()
    client._session = fake_session
    client._auth_token = "token-1"
    return client, fake_session


def _ok(payload):
    resp = MagicMock()
    resp.status_code = HTTPStatus.OK
    resp.json.return_value = payload
    return resp


# ----------------------------------------------------------------------
# Datacenter group calls
# ----------------------------------------------------------------------


def test_list_hits_correct_url() -> None:
    client, session = _make_client_with_fake_session()
    session.get.return_value = _ok([
        {"name": "dc-1", "datacenter": "datacenter-1"},
    ])
    result = client.Datacenter.list()
    url_arg = session.get.call_args.args[0]
    testbase.assert_equal(url_arg, "https://vc.example.com/api/vcenter/datacenter")
    testbase.assert_list_length(result, 1)
    testbase.assert_true(isinstance(result[0], DatacenterSummary))
    return


def test_get_url_includes_id() -> None:
    client, session = _make_client_with_fake_session()
    session.get.return_value = _ok({"name": "dc-name", "datacenter": "datacenter-1"})
    client.Datacenter.get(id="datacenter-1")
    url_arg = session.get.call_args.args[0]
    testbase.assert_equal(url_arg, "https://vc.example.com/api/vcenter/datacenter/datacenter-1")
    return


# ----------------------------------------------------------------------
# Vm group calls
# ----------------------------------------------------------------------


def test_list_uses_sorted_params() -> None:
    client, session = _make_client_with_fake_session()
    session.get.return_value = _ok([])
    client.set_filter_state(datacenter="dc-1", folder="folder-1")
    client.Vm.list()
    params = session.get.call_args.kwargs["params"]
    keys = list(params.keys())
    testbase.assert_equal(keys, sorted(keys))
    testbase.assert_true("datacenters" in params)
    testbase.assert_true("folders" in params)
    return


def test_create_returns_task_handle() -> None:
    from ccai.restclient.vsphere.specs.vmcreate import VmCreateSpec
    from ccai.restclient.vsphere.vspheretaskhandle import VSphereTaskHandle

    client, session = _make_client_with_fake_session()
    post_resp = MagicMock()
    post_resp.status_code = HTTPStatus.OK
    post_resp.json.return_value = "task-12345"
    session.post.return_value = post_resp

    spec = VmCreateSpec(name="vm-new", guest_OS="UBUNTU_64", placement={}, hardware={}, storage={}, networks=[])
    handle = client.Vm.create(spec=spec)
    testbase.assert_true(isinstance(handle, VSphereTaskHandle))
    testbase.assert_equal(handle.task_id(), "task-12345")
    return


# ----------------------------------------------------------------------
# Host group calls
# ----------------------------------------------------------------------


def test_connect_uses_action_param() -> None:
    client, session = _make_client_with_fake_session()
    ok_resp = MagicMock()
    ok_resp.status_code = HTTPStatus.NO_CONTENT
    session.post.return_value = ok_resp
    client.Host.connect(host="host-1")
    params = session.post.call_args.kwargs["params"]
    testbase.assert_equal(params, {"action": "connect"})
    return
