"""
    .. module:: datastoregroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Datastore API group for :class:`VSphereClient`.

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
from automojo.restclient.vsphere.model.datastore import (
    DatastoreInfo,
    DatastoreSummary,
)


class DatastoreGroup(BaseGroup):
    """
        Operations on vSphere datastores (``/api/vcenter/datastore``).
    """

    BASE_LEAF = "/api/vcenter/datastore"

    def get(
        self,
        *,
        name: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> DatastoreInfo:
        """
            Retrieve a datastore detail record.

            :param name: Datastore identifier.
            :param aspects: Behaviour controls.

            :returns: A :class:`DatastoreInfo`.
        """
        client = self.client
        url = self.compose_url(parts=[name])
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="DatastoreGroup.get")
        body = resp.json()
        rtnval = DatastoreInfo.from_dict(body)
        return rtnval

    def list(
        self,
        *,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[DatastoreSummary]:
        """
            List datastores known to vCenter.

            :param aspects: Behaviour controls.

            :returns: List of :class:`DatastoreSummary`.
        """
        client = self.client
        url = self.compose_url()
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="DatastoreGroup.list")
        body = resp.json()
        rtnval = [DatastoreSummary.from_dict(item) for item in body]
        return rtnval
