"""
    .. module:: networkgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Network API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import List, Optional

from http import HTTPStatus

from automojo.errors.raising import raise_for_http_status

from automojo.interop.vsphere.apigroups.basegroup import BaseGroup
from automojo.interop.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from automojo.interop.vsphere.model.network import (
    DistributedSwitchSummary,
    NetworkSummary,
)
from automojo.interop.vsphere.vspheretaskhandle import VSphereTaskHandle


_DVS_LEAF = "/api/vcenter/network/dvs"
_PORTGROUP_LEAF = "/api/vcenter/network/dvportgroup"


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


class NetworkGroup(BaseGroup):
    """
        Operations on vSphere networks (``/api/vcenter/network``).

        Covers plain network enumeration plus the Distributed Virtual
        Switch (DVS) and distributed port group create / delete surface
        the cloud-provisioning venue depends on.  Every create / delete
        operation is asynchronous on vCenter and therefore returns a
        :class:`VSphereTaskHandle`.
    """

    BASE_LEAF = "/api/vcenter/network"

    def list(
        self,
        *,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[NetworkSummary]:
        """
            List networks known to vCenter.

            :param aspects: Behaviour controls.

            :returns: List of :class:`NetworkSummary`.
        """
        client = self.client
        url = self.compose_url()
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="NetworkGroup.list")
        body = resp.json()
        rtnval = [NetworkSummary.from_dict(item) for item in body]
        return rtnval

    # ------------------------------------------------------------------
    # Distributed Virtual Switch
    # ------------------------------------------------------------------

    def create_distributed_switch(
        self,
        *,
        name: str,
        datacenter: str,
        version: Optional[str] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Create a Distributed Virtual Switch.

            :param name: Display name of the new switch.
            :param datacenter: Datacenter identifier the switch lives in.
            :param version: Optional DVS version string.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the create task.
        """
        client = self.client
        url = client.build_url(leaf=_DVS_LEAF)
        payload = {"name": name, "datacenter": datacenter}
        if version is not None:
            payload["version"] = version
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=payload, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.CREATED):
            raise_for_http_status(resp.status_code, resp.content, url, context="NetworkGroup.create_distributed_switch")
        try:
            body = resp.json()
        except Exception:
            body = {}
        task_id = _extract_task_id(payload=body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval

    def delete_distributed_switch(
        self,
        *,
        switch: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Delete a Distributed Virtual Switch.

            :param switch: Distributed switch identifier.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the delete task.
        """
        client = self.client
        url = client.build_url(leaf="{}/{}".format(_DVS_LEAF, switch))
        session = client.ensure_session(aspects=aspects)
        resp = session.delete(url, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.NO_CONTENT):
            raise_for_http_status(resp.status_code, resp.content, url, context="NetworkGroup.delete_distributed_switch")
        try:
            body = resp.json()
        except Exception:
            body = {}
        task_id = _extract_task_id(payload=body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval

    def list_distributed_switches(
        self,
        *,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[DistributedSwitchSummary]:
        """
            List Distributed Virtual Switches known to vCenter.

            :param aspects: Behaviour controls.

            :returns: List of :class:`DistributedSwitchSummary`.
        """
        client = self.client
        url = client.build_url(leaf=_DVS_LEAF)
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="NetworkGroup.list_distributed_switches")
        body = resp.json()
        rtnval = [DistributedSwitchSummary.from_dict(item) for item in body]
        return rtnval

    # ------------------------------------------------------------------
    # Distributed port group
    # ------------------------------------------------------------------

    def create_port_group(
        self,
        *,
        name: str,
        vlan_id: int,
        switch: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Create a distributed port group on the named switch.

            :param name: Port group display name.
            :param vlan_id: VLAN id assigned to the port group.
            :param switch: Owning distributed virtual switch identifier.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the create task.
        """
        client = self.client
        url = client.build_url(leaf=_PORTGROUP_LEAF)
        payload = {"name": name, "vlan_id": vlan_id, "switch": switch}
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=payload, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.CREATED):
            raise_for_http_status(resp.status_code, resp.content, url, context="NetworkGroup.create_port_group")
        try:
            body = resp.json()
        except Exception:
            body = {}
        task_id = _extract_task_id(payload=body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval

    def delete_port_group(
        self,
        *,
        network_id: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Delete a distributed port group.

            :param network_id: Port group identifier.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the delete task.
        """
        client = self.client
        url = client.build_url(leaf="{}/{}".format(_PORTGROUP_LEAF, network_id))
        session = client.ensure_session(aspects=aspects)
        resp = session.delete(url, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.NO_CONTENT):
            raise_for_http_status(resp.status_code, resp.content, url, context="NetworkGroup.delete_port_group")
        try:
            body = resp.json()
        except Exception:
            body = {}
        task_id = _extract_task_id(payload=body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval

    def list_port_groups(
        self,
        *,
        switch: Optional[str] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[NetworkSummary]:
        """
            List distributed port groups, optionally scoped to a switch.

            :param switch: Optional distributed switch identifier filter.
            :param aspects: Behaviour controls.

            :returns: List of :class:`NetworkSummary`.
        """
        client = self.client
        url = client.build_url(leaf=_PORTGROUP_LEAF)
        params = {}
        if switch is not None:
            params["switches"] = [switch]
        sorted_params = self.sort_params(params=params)
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, params=sorted_params, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="NetworkGroup.list_port_groups")
        body = resp.json()
        rtnval = [NetworkSummary.from_dict(item) for item in body]
        return rtnval

    def find_port_group_by_name(
        self,
        *,
        name: str,
        switch: Optional[str] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> Optional[NetworkSummary]:
        """
            Resolve the first distributed port group whose name matches.

            :param name: Port group display name.
            :param switch: Optional distributed switch identifier filter.
            :param aspects: Behaviour controls.

            :returns: A matching :class:`NetworkSummary` or ``None``.
        """
        found = None
        records = self.list_port_groups(switch=switch, aspects=aspects)
        for record in records:
            if record.name == name:
                found = record
                break
        rtnval = found
        return rtnval
