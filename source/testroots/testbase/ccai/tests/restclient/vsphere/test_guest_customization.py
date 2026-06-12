"""
    Tests for guest customization:
    - Linux cloud-init renderer
    - Windows sysprep renderer
    - Hostname validation
    - Network mode validation
    - SSH keys on Windows raises
    - apply_guest_customization_spec returns task handle
"""

import unittest

from http import HTTPStatus
from unittest.mock import MagicMock

from ccai.credentials.basiccredential import BasicCredential
from ccai.errors.exceptions import SemanticError

from ccai.restclient.vsphere.apigroups.customizationrenderers import (
    LinuxCloudInitRenderer,
    WindowsSysprepRenderer,
    validate_hostname,
    validate_network_configs,
)
from ccai.restclient.vsphere.specs.networkconfig import NetworkConfig, NetworkMode
from ccai.restclient.vsphere.specs.vmguestcustomization import (
    VmGuestCustomizationSpec,
)
from ccai.restclient.vsphere.vsphereclient import VSphereClient
from ccai.restclient.vsphere.vspheretaskhandle import VSphereTaskHandle


def _make_client():
    cred = BasicCredential(
        identifier="vc", categories=["basic"], username="u", password="p",
    )
    client = VSphereClient(host="vc.example.com", credential=cred)
    client._session = MagicMock()
    client._auth_token = "tok"
    return client


class TestHostnameValidation(unittest.TestCase):

    def test_valid_hostnames(self) -> None:
        validate_hostname(hostname="vm-1")
        validate_hostname(hostname="abc123")
        validate_hostname(hostname="a")
        return

    def test_invalid_hostnames(self) -> None:
        bad = ["-leading", "trailing-", "UPPER", "with_underscore", "a" * 64, ""]
        for h in bad:
            with self.subTest(hostname=h):
                with self.assertRaises(SemanticError):
                    validate_hostname(hostname=h)
        return


class TestNetworkValidation(unittest.TestCase):

    def test_static_requires_all_fields(self) -> None:
        with self.assertRaises(SemanticError):
            validate_network_configs(network_configs=[
                {"nic_index": 0, "mode": "STATIC", "ipv4_address": "10.0.0.5"},
            ])
        return

    def test_dhcp_with_address_raises(self) -> None:
        with self.assertRaises(SemanticError):
            validate_network_configs(network_configs=[
                {"nic_index": 0, "mode": "DHCP", "ipv4_address": "10.0.0.5",
                 "ipv4_prefix": 24, "ipv4_gateway": "10.0.0.1"},
            ])
        return

    def test_invalid_mode(self) -> None:
        with self.assertRaises(SemanticError):
            validate_network_configs(network_configs=[
                {"nic_index": 0, "mode": "BOGUS"},
            ])
        return

    def test_valid_static(self) -> None:
        validate_network_configs(network_configs=[
            {"nic_index": 0, "mode": "STATIC",
             "ipv4_address": "10.0.0.5", "ipv4_prefix": 24,
             "ipv4_gateway": "10.0.0.1"},
        ])
        return

    def test_valid_dhcp(self) -> None:
        validate_network_configs(network_configs=[
            {"nic_index": 0, "mode": "DHCP"},
        ])
        return


class TestLinuxCloudInitRenderer(unittest.TestCase):

    def test_minimal(self) -> None:
        spec = VmGuestCustomizationSpec(hostname="vm-1")
        rendered = LinuxCloudInitRenderer().render(spec=spec)
        self.assertIn("#cloud-config", rendered)
        self.assertIn("hostname: vm-1", rendered)
        return

    def test_with_dns_and_ssh(self) -> None:
        spec = VmGuestCustomizationSpec(
            hostname="vm-1",
            dns_servers=["8.8.8.8"],
            dns_search=["example.com"],
            ssh_authorized_keys=["ssh-rsa AAAA"],
            run_command_scripts=["echo hello"],
        )
        rendered = LinuxCloudInitRenderer().render(spec=spec)
        self.assertIn("8.8.8.8", rendered)
        self.assertIn("example.com", rendered)
        self.assertIn("ssh-rsa AAAA", rendered)
        self.assertIn("echo hello", rendered)
        return

    def test_invalid_hostname_raises(self) -> None:
        spec = VmGuestCustomizationSpec(hostname="UPPER")
        with self.assertRaises(SemanticError):
            LinuxCloudInitRenderer().render(spec=spec)
        return


class TestWindowsSysprepRenderer(unittest.TestCase):

    def test_minimal(self) -> None:
        spec = VmGuestCustomizationSpec(hostname="vm-1")
        rendered = WindowsSysprepRenderer().render(spec=spec)
        self.assertIn("<?xml", rendered)
        self.assertIn("<ComputerName>vm-1</ComputerName>", rendered)
        return

    def test_first_logon_commands(self) -> None:
        spec = VmGuestCustomizationSpec(
            hostname="vm-1",
            run_command_scripts=["cmd /c echo one", "cmd /c echo two"],
        )
        rendered = WindowsSysprepRenderer().render(spec=spec)
        self.assertIn("FirstLogonCommands", rendered)
        self.assertIn("cmd /c echo one", rendered)
        self.assertIn("cmd /c echo two", rendered)
        return

    def test_ssh_keys_raises(self) -> None:
        spec = VmGuestCustomizationSpec(
            hostname="vm-1",
            ssh_authorized_keys=["ssh-rsa AAAA"],
        )
        with self.assertRaises(SemanticError):
            WindowsSysprepRenderer().render(spec=spec)
        return


class TestApplyGuestCustomization(unittest.TestCase):

    def test_apply_linux_returns_task(self) -> None:
        client = _make_client()
        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.json.return_value = "task-cust-1"
        client._session.post.return_value = resp

        spec = VmGuestCustomizationSpec(hostname="vm-1")
        handle = client.Guest.apply_guest_customization_spec(
            vm="vm-1", spec=spec, guest_os_family="linux",
        )
        self.assertIsInstance(handle, VSphereTaskHandle)
        body = client._session.post.call_args.kwargs["json"]
        self.assertIn("cloud_init_user_data", body)
        return

    def test_apply_windows_returns_task(self) -> None:
        client = _make_client()
        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.json.return_value = "task-cust-2"
        client._session.post.return_value = resp

        spec = VmGuestCustomizationSpec(hostname="vm-1")
        handle = client.Guest.apply_guest_customization_spec(
            vm="vm-1", spec=spec, guest_os_family="windows",
        )
        self.assertIsInstance(handle, VSphereTaskHandle)
        body = client._session.post.call_args.kwargs["json"]
        self.assertIn("sysprep_unattend", body)
        return

    def test_apply_unknown_family_raises(self) -> None:
        client = _make_client()
        spec = VmGuestCustomizationSpec(hostname="vm-1")
        with self.assertRaises(SemanticError):
            client.Guest.apply_guest_customization_spec(
                vm="vm-1", spec=spec, guest_os_family="solaris",
            )
        return


if __name__ == "__main__":
    unittest.main()
