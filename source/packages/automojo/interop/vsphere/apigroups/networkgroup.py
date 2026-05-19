"""
    .. module:: networkgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Network API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import List

from http import HTTPStatus

from automojo.errors.raising import raise_for_http_status

from automojo.interop.vsphere.apigroups.basegroup import BaseGroup
from automojo.interop.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from automojo.interop.vsphere.model.network import NetworkSummary


class NetworkGroup(BaseGroup):
    """
        Operations on vSphere networks (``/api/vcenter/network``).
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
