"""
    .. module:: datacentergroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Datacenter API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import os

from typing import List, Optional

from http import HTTPStatus

from automojo.errors.raising import raise_for_http_status

from automojo.interop.vsphere.apigroups.basegroup import BaseGroup
from automojo.interop.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from automojo.interop.vsphere.model.summary import DatacenterSummary


class DatacenterGroup(BaseGroup):
    """
        Operations on vSphere datacenter objects (``/api/vcenter/datacenter``).
    """

    BASE_LEAF = "/api/vcenter/datacenter"

    def delete(
        self,
        *,
        id: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> None:
        """
            Delete a datacenter.

            :param id: Datacenter identifier.
            :param aspects: Behaviour controls.

            :returns: ``None``
        """
        client = self.client
        url = self.compose_url(parts=[id])
        session = client.ensure_session(aspects=aspects)
        resp = session.delete(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK and resp.status_code != HTTPStatus.NO_CONTENT:
            raise_for_http_status(resp.status_code, resp.content, url, context="DatacenterGroup.delete")
        return None

    def get(
        self,
        *,
        id: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> DatacenterSummary:
        """
            Retrieve a datacenter summary by id.

            :param id: Datacenter identifier.
            :param aspects: Behaviour controls.

            :returns: A :class:`DatacenterSummary`.
        """
        client = self.client
        url = self.compose_url(parts=[id])
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="DatacenterGroup.get")
        body = resp.json()
        rtnval = DatacenterSummary.from_dict(body)
        return rtnval

    def get_by_name(
        self,
        *,
        name: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> Optional[DatacenterSummary]:
        """
            Retrieve the first datacenter with a matching name.

            :param name: Datacenter name to match.
            :param aspects: Behaviour controls.

            :returns: A :class:`DatacenterSummary` or ``None``.
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
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[DatacenterSummary]:
        """
            List all datacenters visible to vCenter.

            :param aspects: Behaviour controls.

            :returns: List of :class:`DatacenterSummary`.
        """
        client = self.client
        url = self.compose_url()
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="DatacenterGroup.list")
        body = resp.json()
        rtnval = [DatacenterSummary.from_dict(item) for item in body]
        return rtnval
