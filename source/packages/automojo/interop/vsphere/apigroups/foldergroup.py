"""
    .. module:: foldergroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Folder API group for :class:`VSphereClient`.

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
from automojo.interop.vsphere.model.summary import (
    DatacenterSummary,
    FolderSummary,
)


class FolderGroup(BaseGroup):
    """
        Operations on vSphere folder objects (``/api/vcenter/folder``).
    """

    BASE_LEAF = "/api/vcenter/folder"

    def list(
        self,
        *,
        datacenters: Optional[List[DatacenterSummary]] = None,
        parent_folders: Optional[List[FolderSummary]] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[FolderSummary]:
        """
            List folders with optional datacenter / parent-folder
            filters.

            :param datacenters: Optional list of datacenters to filter by.
            :param parent_folders: Optional list of parent folders.
            :param aspects: Behaviour controls.

            :returns: List of :class:`FolderSummary`.
        """
        client = self.client
        url = self.compose_url()

        params = {}
        if datacenters is not None:
            params["datacenters"] = [dc.datacenter for dc in datacenters]
        elif client.filter_state.datacenter is not None:
            params["datacenters"] = [client.filter_state.datacenter]

        if parent_folders is not None:
            params["parent_folders"] = [pf.folder for pf in parent_folders]
        elif client.filter_state.folder is not None:
            params["parent_folders"] = [client.filter_state.folder]

        sorted_params = self.sort_params(params=params)

        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, params=sorted_params, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="FolderGroup.list")
        body = resp.json()
        rtnval = [FolderSummary.from_dict(item) for item in body]
        return rtnval

    def find_descendant(
        self,
        *,
        folder_leaf_names: List[str],
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> Optional[FolderSummary]:
        """
            Walk down a folder path one leaf at a time.

            :param folder_leaf_names: Ordered list of folder leaf names.
            :param aspects: Behaviour controls.

            :returns: The leaf :class:`FolderSummary` or ``None``.
        """
        client = self.client

        remaining = [name for name in folder_leaf_names]
        if len(remaining) == 0:
            return None

        filter_dc = client.filter_state.datacenter
        if filter_dc is None:
            datacenters = None
        else:
            datacenters = [DatacenterSummary(name=filter_dc, datacenter=filter_dc)]

        parent_folders: Optional[List[FolderSummary]] = None
        found: Optional[FolderSummary] = None

        while True:
            if len(remaining) == 0:
                break

            next_leaf = remaining.pop(0)
            folders = self.list(
                datacenters=datacenters,
                parent_folders=parent_folders,
                aspects=aspects,
            )

            next_found: Optional[FolderSummary] = None
            for record in folders:
                if record.name == next_leaf:
                    next_found = record
                    break

            if next_found is None:
                found = None
                break

            if len(remaining) > 0:
                parent_folders = [next_found]
            else:
                found = next_found
                break

        rtnval = found
        return rtnval
