"""
    .. module:: customizationrenderers
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Renderers that turn a
        :class:`VmGuestCustomizationSpec` into a guest-OS-specific
        payload — cloud-init for Linux, sysprep unattend.xml for
        Windows.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import os
import re

from typing import Any, Iterable, List, Optional

from automojo.errors.exceptions import SemanticError
from automojo.interop.vsphere.specs.vmguestcustomization import (
    VmGuestCustomizationSpec,
)


_HOSTNAME_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


def validate_hostname(*, hostname: str) -> None:
    """
        Validate a hostname against DNS-label rules.

        :param hostname: Candidate hostname.

        :returns: ``None``

        :raises: SemanticError
    """
    if hostname is None or len(hostname) == 0:
        err_msg_lines = [
            "Guest customization hostname is required.",
        ]
        err_msg = os.linesep.join(err_msg_lines)
        raise SemanticError(err_msg)

    if _HOSTNAME_RE.match(hostname) is None:
        err_msg_lines = [
            "Guest customization hostname violates DNS-label rules.",
            "GOT: {!r}".format(hostname),
            "RULE: lowercase letters/digits/hyphen, 1-63 chars,",
            "      must not start or end with a hyphen",
        ]
        err_msg = os.linesep.join(err_msg_lines)
        raise SemanticError(err_msg)

    return None


def validate_network_configs(*, network_configs: Optional[Iterable[Any]]) -> None:
    """
        Validate that each entry is consistent with its mode.

        :param network_configs: Iterable of dict-like network entries
            or :class:`NetworkConfig` instances.

        :returns: ``None``

        :raises: SemanticError
    """
    if network_configs is None:
        return None

    for entry in network_configs:
        nic_index = _entry_attr(entry=entry, name="nic_index")
        mode = _entry_attr(entry=entry, name="mode")
        ipv4_address = _entry_attr(entry=entry, name="ipv4_address")
        ipv4_prefix = _entry_attr(entry=entry, name="ipv4_prefix")
        ipv4_gateway = _entry_attr(entry=entry, name="ipv4_gateway")

        if mode == "STATIC":
            if ipv4_address is None or ipv4_prefix is None or ipv4_gateway is None:
                err_msg_lines = [
                    "NetworkConfig in STATIC mode is missing required address fields.",
                    "NIC INDEX: {}".format(nic_index),
                    "HAVE: address={!r} prefix={!r} gateway={!r}".format(
                        ipv4_address, ipv4_prefix, ipv4_gateway,
                    ),
                ]
                err_msg = os.linesep.join(err_msg_lines)
                raise SemanticError(err_msg)
        elif mode == "DHCP":
            if ipv4_address is not None or ipv4_prefix is not None or ipv4_gateway is not None:
                err_msg_lines = [
                    "NetworkConfig in DHCP mode must not declare address fields.",
                    "NIC INDEX: {}".format(nic_index),
                ]
                err_msg = os.linesep.join(err_msg_lines)
                raise SemanticError(err_msg)
        else:
            err_msg_lines = [
                "NetworkConfig mode is invalid.",
                "NIC INDEX: {}".format(nic_index),
                "GOT: {!r}".format(mode),
                "EXPECTED: DHCP or STATIC",
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

    return None


def _entry_attr(*, entry: Any, name: str) -> Any:
    """
        Read an attribute or key off either a dict or a SchemaObject.

        :param entry: The candidate record.
        :param name: Field name.

        :returns: The value or ``None`` if absent.
    """
    if isinstance(entry, dict):
        rtnval = entry.get(name)
        return rtnval
    rtnval = getattr(entry, name, None)
    return rtnval


def _spec_field(*, spec: VmGuestCustomizationSpec, name: str) -> Any:
    """
        Read a field from the spec, tolerating absent optional fields.

        :param spec: The customization spec.
        :param name: Field name.

        :returns: The value or ``None``.
    """
    rtnval = getattr(spec, name, None)
    return rtnval


class LinuxCloudInitRenderer:
    """
        Renders a :class:`VmGuestCustomizationSpec` to a cloud-init
        ``#cloud-config`` YAML payload.
    """

    def render(self, *, spec: VmGuestCustomizationSpec) -> str:
        """
            Render the spec to a cloud-init payload.

            :param spec: The customization spec.

            :returns: A cloud-init YAML string.

            :raises: SemanticError
        """
        hostname = _spec_field(spec=spec, name="hostname")
        validate_hostname(hostname=hostname)
        validate_network_configs(
            network_configs=_spec_field(spec=spec, name="network_configs"),
        )

        lines: List[str] = ["#cloud-config", "hostname: {}".format(hostname)]

        dns_servers = _spec_field(spec=spec, name="dns_servers")
        if dns_servers is not None and len(dns_servers) > 0:
            lines.append("manage_resolv_conf: true")
            lines.append("resolv_conf:")
            lines.append("  nameservers:")
            for server in dns_servers:
                lines.append("    - {}".format(server))

        dns_search = _spec_field(spec=spec, name="dns_search")
        if dns_search is not None and len(dns_search) > 0:
            lines.append("  searchdomains:")
            for domain in dns_search:
                lines.append("    - {}".format(domain))

        ssh_keys = _spec_field(spec=spec, name="ssh_authorized_keys")
        if ssh_keys is not None and len(ssh_keys) > 0:
            lines.append("users:")
            lines.append("  - default")
            lines.append("    ssh_authorized_keys:")
            for key in ssh_keys:
                lines.append("      - {}".format(key))

        commands = _spec_field(spec=spec, name="run_command_scripts")
        if commands is not None and len(commands) > 0:
            lines.append("runcmd:")
            for cmd in commands:
                lines.append("  - {}".format(cmd))

        rtnval = os.linesep.join(lines)
        return rtnval


class WindowsSysprepRenderer:
    """
        Renders a :class:`VmGuestCustomizationSpec` to a sysprep
        ``unattend.xml`` payload.
    """

    def render(self, *, spec: VmGuestCustomizationSpec) -> str:
        """
            Render the spec to a sysprep unattend.xml payload.

            :param spec: The customization spec.

            :returns: An XML string.

            :raises: SemanticError
        """
        hostname = _spec_field(spec=spec, name="hostname")
        validate_hostname(hostname=hostname)
        validate_network_configs(
            network_configs=_spec_field(spec=spec, name="network_configs"),
        )

        ssh_keys = _spec_field(spec=spec, name="ssh_authorized_keys")
        if ssh_keys is not None and len(ssh_keys) > 0:
            err_msg_lines = [
                "ssh_authorized_keys is not supported on Windows guests.",
                "COUNT: {}".format(len(ssh_keys)),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

        lines: List[str] = []
        lines.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
        lines.append("<unattend xmlns=\"urn:schemas-microsoft-com:unattend\">")
        lines.append("  <settings pass=\"specialize\">")
        lines.append("    <component name=\"Microsoft-Windows-Shell-Setup\">")
        lines.append("      <ComputerName>{}</ComputerName>".format(hostname))
        lines.append("    </component>")
        lines.append("  </settings>")

        commands = _spec_field(spec=spec, name="run_command_scripts")
        if commands is not None and len(commands) > 0:
            lines.append("  <settings pass=\"oobeSystem\">")
            lines.append("    <component name=\"Microsoft-Windows-Shell-Setup\">")
            lines.append("      <FirstLogonCommands>")
            for index, cmd in enumerate(commands, start=1):
                lines.append("        <SynchronousCommand>")
                lines.append("          <Order>{}</Order>".format(index))
                lines.append("          <CommandLine>{}</CommandLine>".format(cmd))
                lines.append("        </SynchronousCommand>")
            lines.append("      </FirstLogonCommands>")
            lines.append("    </component>")
            lines.append("  </settings>")

        lines.append("</unattend>")

        rtnval = os.linesep.join(lines)
        return rtnval
