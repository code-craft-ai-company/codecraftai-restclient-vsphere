"""
    .. module:: vmgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Virtual machine API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import os
import time

from typing import Callable, List, Optional

from http import HTTPStatus

from automojo.errors.raising import raise_for_http_status

from automojo.interop.vsphere.apigroups.basegroup import BaseGroup
from automojo.interop.vsphere.apigroups.waiters import VSphereWaitTimeoutError
from automojo.interop.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from automojo.interop.vsphere.enums.powerstate import PowerState
from automojo.interop.vsphere.model.summary import (
    DatacenterSummary,
    FolderSummary,
)
from automojo.interop.vsphere.model.vm import (
    VirtualMachineInfo,
    VirtualMachineSummary,
)
from automojo.interop.vsphere.specs.vmcreate import VmCreateSpec
from automojo.interop.vsphere.specs.vmclone import VmCloneSpec
from automojo.interop.vsphere.specs.vmpoweraction import VmPowerActionSpec
from automojo.interop.vsphere.specs.vmsnapshot import VmSnapshotSpec
from automojo.interop.vsphere.vspheretaskhandle import VSphereTaskHandle


class VmGroup(BaseGroup):
    """
        Operations on virtual machines (``/api/vcenter/vm``).
    """

    BASE_LEAF = "/api/vcenter/vm"

    def create(
        self,
        *,
        spec: VmCreateSpec,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Create a new virtual machine.

            :param spec: Aggregate VM-create spec.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the creation task.
        """
        client = self.client
        url = self.compose_url()
        payload = spec.to_dict()
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=payload, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.CREATED):
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.create")
        body = resp.json()
        task_id = _extract_task_id(payload=body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval

    def clone(
        self,
        *,
        spec: VmCloneSpec,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Clone an existing VM.

            :param spec: Clone spec.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the clone task.
        """
        client = self.client
        url = self.compose_url()
        payload = spec.to_dict()
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=payload, params={"action": "clone"}, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.CREATED):
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.clone")
        body = resp.json()
        task_id = _extract_task_id(payload=body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval

    def delete(
        self,
        *,
        id: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> None:
        """
            Delete a VM.

            :param id: VM identifier.
            :param aspects: Behaviour controls.

            :returns: ``None``
        """
        client = self.client
        url = self.compose_url(parts=[id])
        session = client.ensure_session(aspects=aspects)
        resp = session.delete(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK and resp.status_code != HTTPStatus.NO_CONTENT:
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.delete")
        return None

    def get(
        self,
        *,
        id: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VirtualMachineInfo:
        """
            Retrieve VM detail.

            :param id: VM identifier.
            :param aspects: Behaviour controls.

            :returns: A :class:`VirtualMachineInfo`.
        """
        client = self.client
        url = self.compose_url(parts=[id])
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.get")
        body = resp.json()
        rtnval = VirtualMachineInfo.from_dict(body)
        return rtnval

    def get_summary_by_name(
        self,
        *,
        name: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> Optional[VirtualMachineSummary]:
        """
            Retrieve the first VM summary whose name matches.

            :param name: VM display name.
            :param aspects: Behaviour controls.

            :returns: A :class:`VirtualMachineSummary` or ``None``.
        """
        found = None
        records = self.list(aspects=aspects)
        for record in records:
            if record.name == name:
                found = record
                break
        rtnval = found
        return rtnval

    def list(
        self,
        *,
        datacenters: Optional[List[DatacenterSummary]] = None,
        parent_folders: Optional[List[FolderSummary]] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[VirtualMachineSummary]:
        """
            List VMs, optionally filtered.

            :param datacenters: Optional datacenter filter list.
            :param parent_folders: Optional parent folder filter list.
            :param aspects: Behaviour controls.

            :returns: List of :class:`VirtualMachineSummary`.
        """
        client = self.client
        url = self.compose_url()

        params = {}
        if datacenters is not None:
            params["datacenters"] = [dc.datacenter for dc in datacenters]
        elif client.filter_state.datacenter is not None:
            params["datacenters"] = [client.filter_state.datacenter]

        if parent_folders is not None:
            params["folders"] = [pf.folder for pf in parent_folders]
        elif client.filter_state.folder is not None:
            params["folders"] = [client.filter_state.folder]

        sorted_params = self.sort_params(params=params)

        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, params=sorted_params, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.list")
        body = resp.json()
        rtnval = [VirtualMachineSummary.from_dict(item) for item in body]
        return rtnval

    def register(
        self,
        *,
        name: str,
        storage: dict,
        placement: Optional[dict] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> dict:
        """
            Register an existing VM with vCenter.

            :param name: VM name.
            :param storage: Storage description.
            :param placement: Optional placement description.
            :param aspects: Behaviour controls.

            :returns: Raw response payload.
        """
        client = self.client
        url = self.compose_url()
        body = {"name": name}
        body.update(storage)
        if placement is not None:
            body.update(placement)
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=body, params={"action": "register"}, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.register")
        rtnval = resp.json()
        return rtnval

    def relocate(
        self,
        *,
        path: str,
        disks: Optional[dict] = None,
        placement: Optional[dict] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> dict:
        """
            Relocate VM configuration or disks.

            :param path: New datastore path.
            :param disks: Optional disk relocation spec.
            :param placement: Optional placement override.
            :param aspects: Behaviour controls.

            :returns: Raw response payload.
        """
        client = self.client
        url = self.compose_url()
        body = {"path": path}
        if disks is not None:
            body["disks"] = disks
        if placement is not None:
            body.update(placement)
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=body, params={"action": "relocate"}, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.relocate")
        rtnval = resp.json()
        return rtnval

    def unregister(
        self,
        *,
        vmid: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> None:
        """
            Unregister a VM from vCenter.

            :param vmid: VM identifier.
            :param aspects: Behaviour controls.

            :returns: ``None``
        """
        client = self.client
        url = self.compose_url()
        session = client.ensure_session(aspects=aspects)
        resp = session.post(
            url,
            json={"vm": vmid},
            params={"action": "unregister"},
            timeout=aspects.completion_timeout,
        )
        if resp.status_code != HTTPStatus.OK and resp.status_code != HTTPStatus.NO_CONTENT:
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.unregister")
        return None

    def power(
        self,
        *,
        vmid: str,
        spec: VmPowerActionSpec,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Apply a discrete power action to a VM.

            :param vmid: VM identifier.
            :param spec: A :class:`VmPowerActionSpec`.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the operation.
        """
        client = self.client
        url = self.compose_url(parts=[vmid, "power"])
        session = client.ensure_session(aspects=aspects)
        resp = session.post(
            url,
            params={"action": spec.action},
            timeout=aspects.completion_timeout,
        )
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.NO_CONTENT):
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.power")
        try:
            body = resp.json()
        except Exception:
            body = {}
        task_id = _extract_task_id(payload=body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval

    def get_power_state(
        self,
        *,
        vm: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> PowerState:
        """
            Read the current power state of a VM.

            :param vm: VM identifier.
            :param aspects: Behaviour controls.

            :returns: The current :class:`PowerState`.
        """
        client = self.client
        url = self.compose_url(parts=[vm, "power"])
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.get_power_state")
        body = resp.json()
        if isinstance(body, dict):
            raw_state = body.get("state")
            if raw_state is None:
                raw_state = body.get("power_state")
        else:
            raw_state = body
        if raw_state is None:
            err_msg_lines = [
                "VmGroup.get_power_state could not parse the power state.",
                "VM: {}".format(vm),
                "BODY: {!r}".format(body),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise ValueError(err_msg)
        rtnval = PowerState(raw_state)
        return rtnval

    def wait_for_power_state(
        self,
        *,
        vm: str,
        desired: PowerState,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
        state_fetcher: Optional[Callable[[str], PowerState]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> PowerState:
        """
            Poll the power state of a VM until it equals ``desired``.

            The poll cadence is ``aspects.completion_interval``; the
            wall-clock cap is ``aspects.completion_timeout``.  The
            elapsed-time check runs at the top of each iteration so a
            slow GET cannot blow past the timeout.

            :param vm: VM identifier.
            :param desired: Target :class:`PowerState`.
            :param aspects: Behaviour controls.
            :param state_fetcher: Optional injected callable that
                returns the current :class:`PowerState` for a vm-id;
                used by tests to script state sequences without HTTP.
            :param sleeper: Optional override for ``time.sleep``;
                injected by tests.
            :param clock: Optional override for ``time.monotonic``;
                injected by tests.

            :returns: The final :class:`PowerState` (always equal to
                ``desired``).

            :raises: VSphereWaitTimeoutError
        """
        interval = aspects.completion_interval
        timeout = aspects.completion_timeout

        if clock is None:
            clock = time.monotonic
        if sleeper is None:
            sleeper = time.sleep

        if state_fetcher is None:
            def _fetch(vmid: str) -> PowerState:
                inner_rtnval = self.get_power_state(vm=vmid, aspects=aspects)
                return inner_rtnval
            state_fetcher = _fetch

        started = clock()
        last_observed: Optional[PowerState] = None
        rtnval: Optional[PowerState] = None

        while True:
            elapsed = clock() - started
            if elapsed > timeout:
                err_msg_lines = [
                    "VmGroup.wait_for_power_state timed out.",
                    "VM: {}".format(vm),
                    "DESIRED: {}".format(desired.value),
                    "TIMEOUT: {}s".format(timeout),
                    "ELAPSED: {}s".format(elapsed),
                    "LAST OBSERVED: {}".format(
                        last_observed.value if last_observed is not None else "<none>"
                    ),
                ]
                err_msg = os.linesep.join(err_msg_lines)
                raise VSphereWaitTimeoutError(err_msg, observed=last_observed)

            observed = state_fetcher(vm)
            last_observed = observed

            if observed == desired:
                rtnval = observed
                break

            sleeper(interval)

        return rtnval

    def snapshot_create(
        self,
        *,
        vmid: str,
        spec: VmSnapshotSpec,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Take a snapshot of a VM.

            :param vmid: VM identifier.
            :param spec: A :class:`VmSnapshotSpec`.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the snapshot task.
        """
        client = self.client
        url = self.compose_url(parts=[vmid, "snapshot"])
        payload = spec.to_dict()
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=payload, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.CREATED):
            raise_for_http_status(resp.status_code, resp.content, url, context="VmGroup.snapshot_create")
        try:
            body = resp.json()
        except Exception:
            body = {}
        task_id = _extract_task_id(payload=body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval


def _extract_task_id(*, payload) -> str:
    """
        Extract a task id from a vCenter response payload.

        :param payload: The decoded JSON body (str or dict).

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
