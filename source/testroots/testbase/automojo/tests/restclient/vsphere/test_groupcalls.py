"""
    Behavioural tests for a sample of api-group methods, verifying URL
    composition, parameter sorting, and DTO parsing using mocked
    sessions.
"""

import unittest

from http import HTTPStatus
from unittest.mock import MagicMock

from automojo.credentials.basiccredential import BasicCredential

from automojo.restclient.vsphere.aspectsvsphere import DEFAULT_VSPHERE_ASPECTS
from automojo.restclient.vsphere.model.summary import DatacenterSummary, FolderSummary, HostSummary
from automojo.restclient.vsphere.model.vm import VirtualMachineSummary
from automojo.restclient.vsphere.vsphereclient import VSphereClient


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


class TestDatacenterGroupCalls(unittest.TestCase):

    def test_list_hits_correct_url(self) -> None:
        client, session = _make_client_with_fake_session()
        session.get.return_value = _ok([
            {"name": "dc-1", "datacenter": "datacenter-1"},
        ])
        result = client.Datacenter.list()
        url_arg = session.get.call_args.args[0]
        self.assertEqual(url_arg, "https://vc.example.com/api/vcenter/datacenter")
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], DatacenterSummary)
        return

    def test_get_url_includes_id(self) -> None:
        client, session = _make_client_with_fake_session()
        session.get.return_value = _ok({"name": "dc-name", "datacenter": "datacenter-1"})
        client.Datacenter.get(id="datacenter-1")
        url_arg = session.get.call_args.args[0]
        self.assertEqual(url_arg, "https://vc.example.com/api/vcenter/datacenter/datacenter-1")
        return


class TestVmGroupCalls(unittest.TestCase):

    def test_list_uses_sorted_params(self) -> None:
        client, session = _make_client_with_fake_session()
        session.get.return_value = _ok([])
        client.set_filter_state(datacenter="dc-1", folder="folder-1")
        client.Vm.list()
        params = session.get.call_args.kwargs["params"]
        keys = list(params.keys())
        self.assertEqual(keys, sorted(keys))
        self.assertIn("datacenters", params)
        self.assertIn("folders", params)
        return

    def test_create_returns_task_handle(self) -> None:
        from automojo.restclient.vsphere.specs.vmcreate import VmCreateSpec
        from automojo.restclient.vsphere.vspheretaskhandle import VSphereTaskHandle

        client, session = _make_client_with_fake_session()
        post_resp = MagicMock()
        post_resp.status_code = HTTPStatus.OK
        post_resp.json.return_value = "task-12345"
        session.post.return_value = post_resp

        spec = VmCreateSpec(name="vm-new", guest_OS="UBUNTU_64", placement={}, hardware={}, storage={}, networks=[])
        handle = client.Vm.create(spec=spec)
        self.assertIsInstance(handle, VSphereTaskHandle)
        self.assertEqual(handle.task_id(), "task-12345")
        return


class TestHostGroupCalls(unittest.TestCase):

    def test_connect_uses_action_param(self) -> None:
        client, session = _make_client_with_fake_session()
        ok_resp = MagicMock()
        ok_resp.status_code = HTTPStatus.NO_CONTENT
        session.post.return_value = ok_resp
        client.Host.connect(host="host-1")
        params = session.post.call_args.kwargs["params"]
        self.assertEqual(params, {"action": "connect"})
        return


if __name__ == "__main__":
    unittest.main()
