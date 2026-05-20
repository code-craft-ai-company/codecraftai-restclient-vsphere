"""
    Behavioural tests for the API surface added to close the M9
    ``venue-vsphere`` provisioning gaps: NetworkGroup DVS / port-group
    create+delete, TaggingGroup category + tag-association methods,
    VmGroup disk methods, and the ``AspectsVSphere.from_aspects``
    adapter.  HTTP is mocked throughout; no real vCenter is contacted.
"""

import unittest

from http import HTTPStatus
from unittest.mock import MagicMock

from automojo.credentials.basiccredential import BasicCredential

from automojo.interop.vsphere.aspectsvsphere import (
    AspectsVSphere,
    vsphere_aspects_from_aspects,
)
from automojo.interop.vsphere.vsphereclient import VSphereClient
from automojo.interop.vsphere.vspheretaskhandle import VSphereTaskHandle


def _make_client_with_fake_session():
    cred = BasicCredential(
        identifier="vc", categories=["basic"], username="u", password="p"
    )
    client = VSphereClient(host="vc.example.com", credential=cred)
    fake_session = MagicMock()
    client._session = fake_session
    client._auth_token = "token-1"
    return client, fake_session


def _resp(*, status, payload=None):
    resp = MagicMock()
    resp.status_code = status
    if payload is None:
        resp.json.side_effect = ValueError("no body")
    else:
        resp.json.return_value = payload
    return resp


# ----------------------------------------------------------------------
# NetworkGroup — Distributed Virtual Switch
# ----------------------------------------------------------------------


class TestNetworkDistributedSwitch(unittest.TestCase):

    def test_create_distributed_switch_url(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(status=HTTPStatus.OK, payload="task-dvs-1")
        client.Network.create_distributed_switch(name="dvs0", datacenter="dc-1")
        url_arg = session.post.call_args.args[0]
        self.assertEqual(url_arg, "https://vc.example.com/api/vcenter/network/dvs")
        return

    def test_create_distributed_switch_returns_task_handle(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(status=HTTPStatus.OK, payload="task-dvs-1")
        handle = client.Network.create_distributed_switch(
            name="dvs0", datacenter="dc-1"
        )
        self.assertIsInstance(handle, VSphereTaskHandle)
        self.assertEqual(handle.task_id(), "task-dvs-1")
        return

    def test_delete_distributed_switch_url(self) -> None:
        client, session = _make_client_with_fake_session()
        session.delete.return_value = _resp(
            status=HTTPStatus.OK, payload="task-dvs-d"
        )
        client.Network.delete_distributed_switch(switch="dvs-99")
        url_arg = session.delete.call_args.args[0]
        self.assertEqual(
            url_arg, "https://vc.example.com/api/vcenter/network/dvs/dvs-99"
        )
        return

    def test_delete_distributed_switch_returns_task_handle(self) -> None:
        client, session = _make_client_with_fake_session()
        session.delete.return_value = _resp(
            status=HTTPStatus.ACCEPTED, payload="task-dvs-d"
        )
        handle = client.Network.delete_distributed_switch(switch="dvs-99")
        self.assertIsInstance(handle, VSphereTaskHandle)
        self.assertEqual(handle.task_id(), "task-dvs-d")
        return

    def test_list_distributed_switches_parses_summaries(self) -> None:
        client, session = _make_client_with_fake_session()
        session.get.return_value = _resp(
            status=HTTPStatus.OK,
            payload=[{"name": "dvs0", "switch": "dvs-1"}],
        )
        result = client.Network.list_distributed_switches()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].switch, "dvs-1")
        return


# ----------------------------------------------------------------------
# NetworkGroup — Distributed Port Group
# ----------------------------------------------------------------------


class TestNetworkPortGroup(unittest.TestCase):

    def test_create_port_group_url(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(status=HTTPStatus.OK, payload="task-pg-1")
        client.Network.create_port_group(name="pg0", vlan_id=42, switch="dvs-1")
        url_arg = session.post.call_args.args[0]
        self.assertEqual(
            url_arg, "https://vc.example.com/api/vcenter/network/dvportgroup"
        )
        return

    def test_create_port_group_payload(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(status=HTTPStatus.OK, payload="task-pg-1")
        client.Network.create_port_group(name="pg0", vlan_id=42, switch="dvs-1")
        payload = session.post.call_args.kwargs["json"]
        self.assertEqual(payload["vlan_id"], 42)
        self.assertEqual(payload["switch"], "dvs-1")
        return

    def test_create_port_group_returns_task_handle(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(status=HTTPStatus.OK, payload="task-pg-1")
        handle = client.Network.create_port_group(
            name="pg0", vlan_id=42, switch="dvs-1"
        )
        self.assertIsInstance(handle, VSphereTaskHandle)
        self.assertEqual(handle.task_id(), "task-pg-1")
        return

    def test_delete_port_group_url_and_handle(self) -> None:
        client, session = _make_client_with_fake_session()
        session.delete.return_value = _resp(
            status=HTTPStatus.OK, payload="task-pg-d"
        )
        handle = client.Network.delete_port_group(network_id="dvportgroup-7")
        url_arg = session.delete.call_args.args[0]
        self.assertEqual(
            url_arg,
            "https://vc.example.com/api/vcenter/network/dvportgroup/dvportgroup-7",
        )
        self.assertIsInstance(handle, VSphereTaskHandle)
        return

    def test_list_port_groups_scoped_by_switch(self) -> None:
        client, session = _make_client_with_fake_session()
        session.get.return_value = _resp(
            status=HTTPStatus.OK,
            payload=[{"name": "pg0", "network": "dvportgroup-1"}],
        )
        result = client.Network.list_port_groups(switch="dvs-1")
        params = session.get.call_args.kwargs["params"]
        self.assertEqual(params, {"switches": ["dvs-1"]})
        self.assertEqual(len(result), 1)
        return

    def test_find_port_group_by_name_match(self) -> None:
        client, session = _make_client_with_fake_session()
        session.get.return_value = _resp(
            status=HTTPStatus.OK,
            payload=[
                {"name": "pg0", "network": "dvportgroup-1"},
                {"name": "pg1", "network": "dvportgroup-2"},
            ],
        )
        found = client.Network.find_port_group_by_name(name="pg1")
        self.assertIsNotNone(found)
        self.assertEqual(found.network, "dvportgroup-2")
        return

    def test_find_port_group_by_name_no_match(self) -> None:
        client, session = _make_client_with_fake_session()
        session.get.return_value = _resp(status=HTTPStatus.OK, payload=[])
        found = client.Network.find_port_group_by_name(name="missing")
        self.assertIsNone(found)
        return


# ----------------------------------------------------------------------
# TaggingGroup
# ----------------------------------------------------------------------


class TestTaggingGroup(unittest.TestCase):

    def test_ensure_category_creates_when_absent(self) -> None:
        client, session = _make_client_with_fake_session()
        session.get.return_value = _resp(status=HTTPStatus.OK, payload=[])
        session.post.return_value = _resp(
            status=HTTPStatus.OK, payload="category-new"
        )
        category_id = client.Tagging.ensure_category(name="owner")
        post_url = session.post.call_args.args[0]
        self.assertEqual(
            post_url, "https://vc.example.com/api/cis/tagging/category"
        )
        self.assertEqual(category_id, "category-new")
        return

    def test_ensure_category_returns_existing(self) -> None:
        client, session = _make_client_with_fake_session()

        def _get(url, **kwargs):
            if url.endswith("/category"):
                return _resp(status=HTTPStatus.OK, payload=["category-7"])
            return _resp(
                status=HTTPStatus.OK, payload={"name": "owner", "id": "category-7"}
            )

        session.get.side_effect = _get
        category_id = client.Tagging.ensure_category(name="owner")
        self.assertEqual(category_id, "category-7")
        self.assertFalse(session.post.called)
        return

    def test_attach_tag_url_includes_action(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(status=HTTPStatus.NO_CONTENT)
        client.Tagging.attach_tag(
            tag_id="tag-1", object_type="VirtualMachine", object_id="vm-9"
        )
        url_arg = session.post.call_args.args[0]
        self.assertEqual(
            url_arg,
            "https://vc.example.com/api/cis/tagging/tag-association/"
            "id:tag-1?action=attach",
        )
        return

    def test_attach_tag_payload(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(status=HTTPStatus.NO_CONTENT)
        client.Tagging.attach_tag(
            tag_id="tag-1", object_type="VirtualMachine", object_id="vm-9"
        )
        payload = session.post.call_args.kwargs["json"]
        self.assertEqual(
            payload, {"object_id": {"type": "VirtualMachine", "id": "vm-9"}}
        )
        return

    def test_detach_tag_url_includes_action(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(status=HTTPStatus.NO_CONTENT)
        client.Tagging.detach_tag(
            tag_id="tag-1", object_type="VirtualMachine", object_id="vm-9"
        )
        url_arg = session.post.call_args.args[0]
        self.assertEqual(
            url_arg,
            "https://vc.example.com/api/cis/tagging/tag-association/"
            "id:tag-1?action=detach",
        )
        return

    def test_list_attached_objects(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(
            status=HTTPStatus.OK,
            payload={"value": [{"type": "VirtualMachine", "id": "vm-9"}]},
        )
        result = client.Tagging.list_attached_objects(tag_id="tag-1")
        url_arg = session.post.call_args.args[0]
        self.assertIn("action=list-attached-objects", url_arg)
        self.assertEqual(result, [{"type": "VirtualMachine", "id": "vm-9"}])
        return

    def test_list_attached_tags(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(
            status=HTTPStatus.OK, payload=["tag-1", "tag-2"]
        )
        result = client.Tagging.list_attached_tags(
            object_type="VirtualMachine", object_id="vm-9"
        )
        url_arg = session.post.call_args.args[0]
        self.assertIn("action=list-attached-tags", url_arg)
        self.assertEqual(result, ["tag-1", "tag-2"])
        return


# ----------------------------------------------------------------------
# VmGroup — disk methods
# ----------------------------------------------------------------------


class TestVmDiskMethods(unittest.TestCase):

    def test_attach_disk_url(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(
            status=HTTPStatus.OK, payload="task-disk-1"
        )
        client.Vm.attach_disk(vm_id="vm-9", datastore_id="ds-1", size_gb=20)
        url_arg = session.post.call_args.args[0]
        self.assertEqual(
            url_arg, "https://vc.example.com/api/vcenter/vm/vm-9/hardware/disk"
        )
        return

    def test_attach_disk_capacity_in_bytes(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(
            status=HTTPStatus.OK, payload="task-disk-1"
        )
        client.Vm.attach_disk(vm_id="vm-9", datastore_id="ds-1", size_gb=20)
        payload = session.post.call_args.kwargs["json"]
        self.assertEqual(payload["new_vmdk"]["capacity"], 20 * 1024 * 1024 * 1024)
        self.assertEqual(payload["backing"]["datastore"], "ds-1")
        return

    def test_attach_disk_returns_task_handle(self) -> None:
        client, session = _make_client_with_fake_session()
        session.post.return_value = _resp(
            status=HTTPStatus.OK, payload="task-disk-1"
        )
        handle = client.Vm.attach_disk(
            vm_id="vm-9", datastore_id="ds-1", size_gb=20
        )
        self.assertIsInstance(handle, VSphereTaskHandle)
        self.assertEqual(handle.task_id(), "task-disk-1")
        return

    def test_detach_disk_url_and_handle(self) -> None:
        client, session = _make_client_with_fake_session()
        session.delete.return_value = _resp(
            status=HTTPStatus.OK, payload="task-disk-d"
        )
        handle = client.Vm.detach_disk(vm_id="vm-9", disk_id="disk-3")
        url_arg = session.delete.call_args.args[0]
        self.assertEqual(
            url_arg,
            "https://vc.example.com/api/vcenter/vm/vm-9/hardware/disk/disk-3",
        )
        self.assertIsInstance(handle, VSphereTaskHandle)
        return

    def test_list_disks(self) -> None:
        client, session = _make_client_with_fake_session()
        session.get.return_value = _resp(
            status=HTTPStatus.OK, payload=[{"disk": "disk-3"}]
        )
        result = client.Vm.list_disks(vm_id="vm-9")
        url_arg = session.get.call_args.args[0]
        self.assertEqual(
            url_arg, "https://vc.example.com/api/vcenter/vm/vm-9/hardware/disk"
        )
        self.assertEqual(result, [{"disk": "disk-3"}])
        return


# ----------------------------------------------------------------------
# Aspects adapter
# ----------------------------------------------------------------------


class _FakeProvisioningAspects:
    """
        Stand-in for ProvisioningAspects exposing verify_* field names.
    """

    def __init__(self, *, dry_run=False, verify_timeout=600.0,
                 verify_interval=10.0):
        self.dry_run = dry_run
        self.verify_timeout = verify_timeout
        self.verify_interval = verify_interval
        return


class TestAspectsAdapter(unittest.TestCase):

    def test_from_aspects_maps_verify_fields(self) -> None:
        src = _FakeProvisioningAspects(verify_timeout=120.0, verify_interval=5.0)
        result = AspectsVSphere.from_aspects(src)
        self.assertIsInstance(result, AspectsVSphere)
        self.assertEqual(result.completion_timeout, 120.0)
        self.assertEqual(result.completion_interval, 5.0)
        return

    def test_from_aspects_passthrough_for_native(self) -> None:
        native = AspectsVSphere(completion_timeout=99.0)
        result = AspectsVSphere.from_aspects(native)
        self.assertIs(result, native)
        return

    def test_from_aspects_none_yields_default(self) -> None:
        result = AspectsVSphere.from_aspects(None)
        self.assertIsInstance(result, AspectsVSphere)
        self.assertEqual(result.completion_timeout, 30.0)
        return

    def test_function_form_matches_classmethod(self) -> None:
        src = _FakeProvisioningAspects(verify_timeout=77.0)
        result = vsphere_aspects_from_aspects(aspects=src)
        self.assertEqual(result.completion_timeout, 77.0)
        return

    def test_from_aspects_prefers_completion_named_fields(self) -> None:
        class _Mixed:
            completion_timeout = 11.0
            verify_timeout = 22.0
            completion_interval = 1.0
            verify_interval = 2.0

        result = AspectsVSphere.from_aspects(_Mixed())
        self.assertEqual(result.completion_timeout, 11.0)
        self.assertEqual(result.completion_interval, 1.0)
        return


if __name__ == "__main__":
    unittest.main()
