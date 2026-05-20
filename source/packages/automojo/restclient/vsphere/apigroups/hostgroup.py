"""
    .. module:: hostgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: ESXi host API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import List

from http import HTTPStatus

from automojo.errors.raising import raise_for_http_status

from automojo.restclient.vsphere.apigroups.basegroup import BaseGroup
from automojo.restclient.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from automojo.restclient.vsphere.model.summary import HostSummary


class HostGroup(BaseGroup):
    """
        Operations on ESXi hosts (``/api/vcenter/host``).
    """

    BASE_LEAF = "/api/vcenter/host"

    def connect(
        self,
        *,
        host: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> None:
        """
            Connect a host to vCenter.

            :param host: Host identifier.
            :param aspects: Behaviour controls.

            :returns: ``None``
        """
        client = self.client
        url = self.compose_url(parts=[host])
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, params={"action": "connect"}, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK and resp.status_code != HTTPStatus.NO_CONTENT:
            raise_for_http_status(resp.status_code, resp.content, url, context="HostGroup.connect")
        return None

    def delete(
        self,
        *,
        host: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> None:
        """
            Delete a host from vCenter inventory.

            :param host: Host identifier.
            :param aspects: Behaviour controls.

            :returns: ``None``
        """
        client = self.client
        url = self.compose_url(parts=[host])
        session = client.ensure_session(aspects=aspects)
        resp = session.delete(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK and resp.status_code != HTTPStatus.NO_CONTENT:
            raise_for_http_status(resp.status_code, resp.content, url, context="HostGroup.delete")
        return None

    def disconnect(
        self,
        *,
        host: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> None:
        """
            Disconnect a host from vCenter.

            :param host: Host identifier.
            :param aspects: Behaviour controls.

            :returns: ``None``
        """
        client = self.client
        url = self.compose_url(parts=[host])
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, params={"action": "disconnect"}, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK and resp.status_code != HTTPStatus.NO_CONTENT:
            raise_for_http_status(resp.status_code, resp.content, url, context="HostGroup.disconnect")
        return None

    def list(
        self,
        *,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[HostSummary]:
        """
            List hosts known to vCenter.

            :param aspects: Behaviour controls.

            :returns: List of :class:`HostSummary`.
        """
        client = self.client
        url = self.compose_url()
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="HostGroup.list")
        body = resp.json()
        rtnval = [HostSummary.from_dict(item) for item in body]
        return rtnval
