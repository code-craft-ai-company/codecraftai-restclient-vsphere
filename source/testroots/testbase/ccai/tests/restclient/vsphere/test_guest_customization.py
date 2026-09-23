"""
    Tests for guest customization:
    - Linux cloud-init renderer
    - Windows sysprep renderer
    - Hostname validation
    - Network mode validation
    - SSH keys on Windows raises
    - apply_guest_customization_spec returns task handle
"""


from http import HTTPStatus
from unittest.mock import MagicMock

from ccai import testbase

from ccai.credentials.basiccredential import BasicCredential
from ccai.errors.exceptions import SemanticError

from ccai.restclient.vsphere.apigroups.customizationrenderers import (
    LinuxCloudInitRenderer,
    WindowsSysprepRenderer,
    validate_hostname,
    validate_network_configs,
)
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


# ----------------------------------------------------------------------
# TestHostnameValidation
# ----------------------------------------------------------------------


def test_valid_hostnames() -> None:
    validate_hostname(hostname="vm-1")
    validate_hostname(hostname="abc123")
    validate_hostname(hostname="a")
    return

def test_invalid_hostnames() -> None:
    bad = ["-leading", "trailing-", "UPPER", "with_underscore", "a" * 64, ""]
    for h in bad:
        with testbase.raises(SemanticError):
            validate_hostname(hostname=h)
    return


# ----------------------------------------------------------------------
# TestNetworkValidation
# ----------------------------------------------------------------------


def test_static_requires_all_fields() -> None:
    with testbase.raises(SemanticError):
        validate_network_configs(network_configs=[
            {"nic_index": 0, "mode": "STATIC", "ipv4_address": "10.0.0.5"},
        ])
    return

def test_dhcp_with_address_raises() -> None:
    with testbase.raises(SemanticError):
        validate_network_configs(network_configs=[
            {"nic_index": 0, "mode": "DHCP", "ipv4_address": "10.0.0.5",
             "ipv4_prefix": 24, "ipv4_gateway": "10.0.0.1"},
        ])
    return

def test_invalid_mode() -> None:
    with testbase.raises(SemanticError):
        validate_network_configs(network_configs=[
            {"nic_index": 0, "mode": "BOGUS"},
        ])
    return

def test_valid_static() -> None:
    validate_network_configs(network_configs=[
        {"nic_index": 0, "mode": "STATIC",
         "ipv4_address": "10.0.0.5", "ipv4_prefix": 24,
         "ipv4_gateway": "10.0.0.1"},
    ])
    return

def test_valid_dhcp() -> None:
    validate_network_configs(network_configs=[
        {"nic_index": 0, "mode": "DHCP"},
    ])
    return


# ----------------------------------------------------------------------
# TestLinuxCloudInitRenderer
# ----------------------------------------------------------------------


def test_linux_cloud_init_minimal() -> None:
    spec = VmGuestCustomizationSpec(hostname="vm-1")
    rendered = LinuxCloudInitRenderer().render(spec=spec)
    testbase.assert_true("#cloud-config" in rendered)
    testbase.assert_true("hostname: vm-1" in rendered)
    return

def test_with_dns_and_ssh() -> None:
    spec = VmGuestCustomizationSpec(
        hostname="vm-1",
        dns_servers=["8.8.8.8"],
        dns_search=["example.com"],
        ssh_authorized_keys=["ssh-rsa AAAA"],
        run_command_scripts=["echo hello"],
    )
    rendered = LinuxCloudInitRenderer().render(spec=spec)
    testbase.assert_true("8.8.8.8" in rendered)
    testbase.assert_true("example.com" in rendered)
    testbase.assert_true("ssh-rsa AAAA" in rendered)
    testbase.assert_true("echo hello" in rendered)
    return

def test_invalid_hostname_raises() -> None:
    spec = VmGuestCustomizationSpec(hostname="UPPER")
    with testbase.raises(SemanticError):
        LinuxCloudInitRenderer().render(spec=spec)
    return


# ----------------------------------------------------------------------
# TestWindowsSysprepRenderer
# ----------------------------------------------------------------------


def test_windows_sysprep_minimal() -> None:
    spec = VmGuestCustomizationSpec(hostname="vm-1")
    rendered = WindowsSysprepRenderer().render(spec=spec)
    testbase.assert_true("<?xml" in rendered)
    testbase.assert_true("<ComputerName>vm-1</ComputerName>" in rendered)
    return

def test_first_logon_commands() -> None:
    spec = VmGuestCustomizationSpec(
        hostname="vm-1",
        run_command_scripts=["cmd /c echo one", "cmd /c echo two"],
    )
    rendered = WindowsSysprepRenderer().render(spec=spec)
    testbase.assert_true("FirstLogonCommands" in rendered)
    testbase.assert_true("cmd /c echo one" in rendered)
    testbase.assert_true("cmd /c echo two" in rendered)
    return

def test_ssh_keys_raises() -> None:
    spec = VmGuestCustomizationSpec(
        hostname="vm-1",
        ssh_authorized_keys=["ssh-rsa AAAA"],
    )
    with testbase.raises(SemanticError):
        WindowsSysprepRenderer().render(spec=spec)
    return


# ----------------------------------------------------------------------
# TestApplyGuestCustomization
# ----------------------------------------------------------------------


def test_apply_linux_returns_task() -> None:
    client = _make_client()
    resp = MagicMock()
    resp.status_code = HTTPStatus.OK
    resp.json.return_value = "task-cust-1"
    client._session.post.return_value = resp

    spec = VmGuestCustomizationSpec(hostname="vm-1")
    handle = client.Guest.apply_guest_customization_spec(
        vm="vm-1", spec=spec, guest_os_family="linux",
    )
    testbase.assert_true(isinstance(handle, VSphereTaskHandle))
    body = client._session.post.call_args.kwargs["json"]
    testbase.assert_true("cloud_init_user_data" in body)
    return

def test_apply_windows_returns_task() -> None:
    client = _make_client()
    resp = MagicMock()
    resp.status_code = HTTPStatus.OK
    resp.json.return_value = "task-cust-2"
    client._session.post.return_value = resp

    spec = VmGuestCustomizationSpec(hostname="vm-1")
    handle = client.Guest.apply_guest_customization_spec(
        vm="vm-1", spec=spec, guest_os_family="windows",
    )
    testbase.assert_true(isinstance(handle, VSphereTaskHandle))
    body = client._session.post.call_args.kwargs["json"]
    testbase.assert_true("sysprep_unattend" in body)
    return

def test_apply_unknown_family_raises() -> None:
    client = _make_client()
    spec = VmGuestCustomizationSpec(hostname="vm-1")
    with testbase.raises(SemanticError):
        client.Guest.apply_guest_customization_spec(
            vm="vm-1", spec=spec, guest_os_family="solaris",
        )
    return
