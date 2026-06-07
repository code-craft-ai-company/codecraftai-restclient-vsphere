"""
    .. module:: guestgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Guest OS operations API group for :class:`VSphereClient`.
        Adds the VMware-Tools-ready and IP-address waiters, plus the
        guest-customization apply method.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


import os
import time

from http import HTTPStatus

from typing import Any, Callable, List, Optional

from ccai.errors.exceptions import SemanticError
from ccai.errors.raising import raise_for_http_status

from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup
from ccai.restclient.vsphere.apigroups.customizationrenderers import (
    LinuxCloudInitRenderer,
    WindowsSysprepRenderer,
)
from ccai.restclient.vsphere.apigroups.waiters import (
    VSphereWaitInvalidStateError,
    VSphereWaitTimeoutError,
)
from ccai.restclient.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from ccai.restclient.vsphere.enums.powerstate import PowerState
from ccai.restclient.vsphere.specs.vmguestcustomization import (
    VmGuestCustomizationSpec,
)
from ccai.restclient.vsphere.vspheretaskhandle import VSphereTaskHandle


IP_FAMILY_IPV4 = "ipv4"
IP_FAMILY_IPV6 = "ipv6"

TOOLS_STATE_RUNNING = "RUNNING"


class GuestGroup(BaseGroup):
    """
        Guest OS operations.

        Hosts the in-guest waiter methods (tools-ready, ip-address) and
        the customization-apply entry point.  The poll loops are
        Aspects-driven and accept injected ``state_fetcher`` / ``clock``
        / ``sleeper`` callables so tests can drive deterministic state
        sequences without real time.
    """

    BASE_LEAF = "/api/vcenter/vm"

    GUEST_IDENTITY_LEAF = "/guest/identity"
    GUEST_NETWORKING_LEAF = "/guest/networking/interfaces"
    GUEST_LOCAL_FILESYSTEM_LEAF = "/guest/local-filesystem"
    GUEST_CUSTOMIZATION_LEAF = "/guest/customization"

    # ------------------------------------------------------------------
    # Tools-ready waiter
    # ------------------------------------------------------------------

    def get_tools_state(
        self,
        *,
        vm: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> str:
        """
            Read the VMware Tools state for a VM.

            :param vm: VM identifier.
            :param aspects: Behaviour controls.

            :returns: A tools-state string (e.g. ``"RUNNING"``,
                ``"NOT_RUNNING"``, ``"STARTING"``).
        """
        client = self.client
        leaf = "{}/{}/tools".format(self.BASE_LEAF, vm)
        url = client.build_url(leaf=leaf)
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="GuestGroup.get_tools_state")
        body = resp.json()
        if isinstance(body, dict):
            raw_state = body.get("run_state")
            if raw_state is None:
                raw_state = body.get("state")
        else:
            raw_state = body
        rtnval = "" if raw_state is None else str(raw_state)
        return rtnval

    def wait_for_tools_ready(
        self,
        *,
        vm: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
        state_fetcher: Optional[Callable[[str], str]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> str:
        """
            Poll the VMware Tools state until it reports ``RUNNING``.

            :param vm: VM identifier.
            :param aspects: Behaviour controls.
            :param state_fetcher: Optional injected callable that
                returns the current tools-state string for a vm-id.
            :param sleeper: Optional override for ``time.sleep``.
            :param clock: Optional override for ``time.monotonic``.

            :returns: The final tools-state string (always ``RUNNING``).

            :raises: VSphereWaitTimeoutError
        """
        interval = aspects.completion_interval
        timeout = aspects.completion_timeout

        if clock is None:
            clock = time.monotonic
        if sleeper is None:
            sleeper = time.sleep

        if state_fetcher is None:
            def _fetch(vmid: str) -> str:
                inner_rtnval = self.get_tools_state(vm=vmid, aspects=aspects)
                return inner_rtnval
            state_fetcher = _fetch

        started = clock()
        last_observed: Optional[str] = None
        rtnval: Optional[str] = None

        while True:
            elapsed = clock() - started
            if elapsed > timeout:
                err_msg_lines = [
                    "GuestGroup.wait_for_tools_ready timed out.",
                    "VM: {}".format(vm),
                    "TIMEOUT: {}s".format(timeout),
                    "ELAPSED: {}s".format(elapsed),
                    "LAST OBSERVED: {!r}".format(last_observed),
                ]
                err_msg = os.linesep.join(err_msg_lines)
                raise VSphereWaitTimeoutError(err_msg, observed=last_observed)

            observed = state_fetcher(vm)
            last_observed = observed

            if observed == TOOLS_STATE_RUNNING:
                rtnval = observed
                break

            sleeper(interval)

        return rtnval

    # ------------------------------------------------------------------
    # IP-address waiter
    # ------------------------------------------------------------------

    def get_guest_networking(
        self,
        *,
        vm: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[dict]:
        """
            Retrieve the guest NIC inventory reported via tools.

            :param vm: VM identifier.
            :param aspects: Behaviour controls.

            :returns: List of NIC dicts as reported by vCenter.
        """
        client = self.client
        leaf = "{}/{}{}".format(self.BASE_LEAF, vm, self.GUEST_NETWORKING_LEAF)
        url = client.build_url(leaf=leaf)
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(
                resp.status_code, resp.content, url, context="GuestGroup.get_guest_networking",
            )
        body = resp.json()
        if isinstance(body, list):
            rtnval = body
        else:
            rtnval = []
        return rtnval

    def wait_for_ip_address(
        self,
        *,
        vm: str,
        nic_index: int = 0,
        family: str = IP_FAMILY_IPV4,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
        networking_fetcher: Optional[Callable[[str], List[dict]]] = None,
        power_state_fetcher: Optional[Callable[[str], PowerState]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> str:
        """
            Poll the guest's NIC inventory until a non-empty address is
            reported for ``nic_index`` in the requested ``family``.

            If the VM is observed to transition to ``POWERED_OFF`` mid-
            wait, :class:`VSphereWaitInvalidStateError` is raised — the
            address will never arrive.

            :param vm: VM identifier.
            :param nic_index: Zero-based NIC ordinal.
            :param family: ``"ipv4"`` or ``"ipv6"``.
            :param aspects: Behaviour controls.
            :param networking_fetcher: Optional injected callable that
                returns the current NIC list for a vm-id.
            :param power_state_fetcher: Optional injected callable
                returning the current :class:`PowerState`; used by tests
                to script a mid-wait power-off scenario.
            :param sleeper: Optional override for ``time.sleep``.
            :param clock: Optional override for ``time.monotonic``.

            :returns: The IP address string.

            :raises: VSphereWaitTimeoutError, VSphereWaitInvalidStateError,
                SemanticError
        """
        if family != IP_FAMILY_IPV4 and family != IP_FAMILY_IPV6:
            err_msg_lines = [
                "GuestGroup.wait_for_ip_address: 'family' must be 'ipv4' or 'ipv6'.",
                "GOT: {!r}".format(family),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

        interval = aspects.completion_interval
        timeout = aspects.completion_timeout

        if clock is None:
            clock = time.monotonic
        if sleeper is None:
            sleeper = time.sleep

        if networking_fetcher is None:
            def _fetch_nics(vmid: str) -> List[dict]:
                inner_rtnval = self.get_guest_networking(vm=vmid, aspects=aspects)
                return inner_rtnval
            networking_fetcher = _fetch_nics

        started = clock()
        last_observed: Optional[List[dict]] = None
        rtnval: Optional[str] = None

        while True:
            elapsed = clock() - started
            if elapsed > timeout:
                err_msg_lines = [
                    "GuestGroup.wait_for_ip_address timed out.",
                    "VM: {}".format(vm),
                    "NIC INDEX: {}".format(nic_index),
                    "FAMILY: {}".format(family),
                    "TIMEOUT: {}s".format(timeout),
                    "ELAPSED: {}s".format(elapsed),
                ]
                err_msg = os.linesep.join(err_msg_lines)
                raise VSphereWaitTimeoutError(err_msg, observed=last_observed)

            if power_state_fetcher is not None:
                ps = power_state_fetcher(vm)
                if ps == PowerState.POWERED_OFF:
                    err_msg_lines = [
                        "GuestGroup.wait_for_ip_address observed VM powered off.",
                        "VM: {}".format(vm),
                        "OBSERVED: {}".format(ps.value),
                    ]
                    err_msg = os.linesep.join(err_msg_lines)
                    raise VSphereWaitInvalidStateError(err_msg, observed=ps)

            nics = networking_fetcher(vm)
            last_observed = nics

            address = _extract_ip(
                nics=nics, nic_index=nic_index, family=family,
            )
            if address is not None and len(address) > 0:
                rtnval = address
                break

            sleeper(interval)

        return rtnval

    # ------------------------------------------------------------------
    # Guest customization
    # ------------------------------------------------------------------

    def apply_guest_customization_spec(
        self,
        *,
        vm: str,
        spec: VmGuestCustomizationSpec,
        guest_os_family: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Render and apply a :class:`VmGuestCustomizationSpec`.

            The ``guest_os_family`` controls renderer dispatch.  The
            value is intentionally passed by the caller (rather than
            sniffed inside the call) so the apply step is decoupled
            from the inventory-detection step and remains testable
            without a live VM.

            :param vm: VM identifier.
            :param spec: Customization spec.
            :param guest_os_family: ``"linux"`` or ``"windows"``.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the apply task.

            :raises: SemanticError
        """
        family = guest_os_family.lower()
        if family == "linux":
            renderer = LinuxCloudInitRenderer()
            payload_key = "cloud_init_user_data"
        elif family == "windows":
            renderer = WindowsSysprepRenderer()
            payload_key = "sysprep_unattend"
        else:
            err_msg_lines = [
                "Unsupported guest_os_family for customization.",
                "GOT: {!r}".format(guest_os_family),
                "EXPECTED: 'linux' or 'windows'",
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

        rendered = renderer.render(spec=spec)

        client = self.client
        leaf = "{}/{}{}".format(self.BASE_LEAF, vm, self.GUEST_CUSTOMIZATION_LEAF)
        url = client.build_url(leaf=leaf)
        body = {
            "hostname": getattr(spec, "hostname", None),
            payload_key: rendered,
        }
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=body, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.CREATED, HTTPStatus.NO_CONTENT):
            raise_for_http_status(
                resp.status_code, resp.content, url,
                context="GuestGroup.apply_guest_customization_spec",
            )
        try:
            response_body = resp.json()
        except ValueError:
            response_body = {}
        task_id = _extract_task_id(payload=response_body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval


def _extract_ip(
    *,
    nics: List[dict],
    nic_index: int,
    family: str,
) -> Optional[str]:
    """
        Pull an address of the requested family for the NIC ordinal
        out of a vCenter networking payload.

        :param nics: The NIC list as returned by vCenter.
        :param nic_index: Zero-based NIC ordinal.
        :param family: ``"ipv4"`` or ``"ipv6"``.

        :returns: The address string or ``None`` if not yet present.
    """
    if nics is None:
        return None
    if len(nics) <= nic_index:
        return None

    entry = nics[nic_index]
    if not isinstance(entry, dict):
        return None

    ip_block = entry.get("ip")
    if not isinstance(ip_block, dict):
        ip_block = entry

    candidates = ip_block.get("ip_addresses")
    if candidates is None:
        candidates = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        ip_family = candidate.get("ip_address_family")
        if ip_family is None:
            ip_family = candidate.get("family")
        if ip_family is None:
            continue
        normalized = str(ip_family).lower()
        if "ipv4" in normalized and family == IP_FAMILY_IPV4:
            address = candidate.get("ip_address")
            if address is None:
                address = candidate.get("address")
            if address is not None and len(str(address)) > 0:
                rtnval = str(address)
                return rtnval
        if "ipv6" in normalized and family == IP_FAMILY_IPV6:
            address = candidate.get("ip_address")
            if address is None:
                address = candidate.get("address")
            if address is not None and len(str(address)) > 0:
                rtnval = str(address)
                return rtnval

    return None


def _extract_task_id(*, payload) -> str:
    """
        Extract a task id from a vCenter response payload.

        :param payload: Decoded JSON body (str or dict).

        :returns: The task identifier string.
    """
    if isinstance(payload, str):
        rtnval = payload
        return rtnval
    if isinstance(payload, dict):
        if "task" in payload:
            candidate = payload["task"]
            if isinstance(candidate, str):
                rtnval = candidate
                return rtnval
        if "value" in payload:
            candidate = payload["value"]
            if isinstance(candidate, str):
                rtnval = candidate
                return rtnval
    rtnval = "" if payload is None else str(payload)
    return rtnval
