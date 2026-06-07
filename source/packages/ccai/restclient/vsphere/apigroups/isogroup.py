"""
    .. module:: isogroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: ISO mount/unmount API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from http import HTTPStatus

from ccai.errors.raising import raise_for_http_status

from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup
from ccai.restclient.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)


class IsoGroup(BaseGroup):
    """
        Operations on the ISO image surface (``/api/vcenter/iso/image``).
    """

    BASE_LEAF = "/api/vcenter/iso/image"

    def mount(
        self,
        *,
        vm: str,
        library_item: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> dict:
        """
            Mount a content library item to a VM as an ISO.

            :param vm: VM identifier.
            :param library_item: Content library item identifier.
            :param aspects: Behaviour controls.

            :returns: Raw response payload.
        """
        client = self.client
        url = self.compose_url()
        body = {"vm": vm, "library_item": library_item}
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=body, params={"action": "mount"}, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="IsoGroup.mount")
        rtnval = resp.json()
        return rtnval

    def unmount(
        self,
        *,
        vm: str,
        cdrom: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> dict:
        """
            Unmount an ISO from a VM's CD-ROM device.

            :param vm: VM identifier.
            :param cdrom: CD-ROM device identifier.
            :param aspects: Behaviour controls.

            :returns: Raw response payload.
        """
        client = self.client
        url = self.compose_url()
        body = {"vm": vm, "cdrom": cdrom}
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=body, params={"action": "unmount"}, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="IsoGroup.unmount")
        rtnval = resp.json()
        return rtnval
