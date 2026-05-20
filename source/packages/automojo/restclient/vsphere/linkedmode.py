"""
    .. module:: linkedmode
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Helpers wrapping the vSphere Linked Mode (HVC) surface.
        The helpers live next to :class:`VSphereClient` rather than on a
        ``*Group`` because they return either a list of metadata
        records or a new client instance — they are client-shaped
        concerns.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import os

from http import HTTPStatus
from typing import List, Optional, TYPE_CHECKING

from automojo.errors.raising import raise_for_http_status

from automojo.restclient.vsphere.apigroups.inventoryerrors import (
    VSphereResourceNotFoundError,
)
from automojo.restclient.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from automojo.restclient.vsphere.model.linkedvcenter import LinkedVCenterRecord


if TYPE_CHECKING:
    from automojo.restclient.vsphere.vsphereclient import VSphereClient


HVC_LINKS_LEAF = "/api/vcenter/hvc/links"


def list_linked_vcenters(
    *,
    client: "VSphereClient",
    aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
) -> List[LinkedVCenterRecord]:
    """
        Enumerate vCenters federated with ``client`` via Linked Mode.

        When linked mode is not configured the function returns a
        single-entry list containing only the local vCenter — derived
        from the client's host attribute and (when reachable) the
        ``/api/appliance/system/version`` response.

        :param client: The originating :class:`VSphereClient`.
        :param aspects: Behaviour controls.

        :returns: List of :class:`LinkedVCenterRecord`.
    """
    url = client.build_url(leaf=HVC_LINKS_LEAF)
    session = client.ensure_session(aspects=aspects)
    resp = session.get(url, timeout=aspects.completion_timeout)

    if resp.status_code == HTTPStatus.NOT_FOUND:
        local = _build_local_record(client=client)
        rtnval = [local]
        return rtnval

    if resp.status_code != HTTPStatus.OK:
        raise_for_http_status(
            resp.status_code, resp.content, url,
            context="linkedmode.list_linked_vcenters",
        )

    body = resp.json()
    records: List[LinkedVCenterRecord] = []
    if not isinstance(body, list):
        local = _build_local_record(client=client)
        records.append(local)
        rtnval = records
        return rtnval

    if len(body) == 0:
        local = _build_local_record(client=client)
        records.append(local)
        rtnval = records
        return rtnval

    for raw in body:
        if not isinstance(raw, dict):
            continue
        records.append(LinkedVCenterRecord.from_dict(raw))
    rtnval = records
    return rtnval


def build_scoped_client(
    *,
    client: "VSphereClient",
    uuid: str,
    aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    linked: Optional[List[LinkedVCenterRecord]] = None,
) -> "VSphereClient":
    """
        Return a :class:`VSphereClient` scoped to the linked vCenter
        identified by ``uuid``.

        The implementation is deliberately conservative: when the
        target uuid matches the local vCenter (``is_local=True``) the
        same client instance is returned; for a peer, a new
        :class:`VSphereClient` is constructed against the peer
        hostname and the same credentials.  Tests inject the resolved
        ``linked`` list to bypass HTTP.

        :param client: Originating client.
        :param uuid: Target vCenter UUID.
        :param aspects: Behaviour controls.
        :param linked: Optional pre-resolved record list.

        :returns: A :class:`VSphereClient` scoped to the named vCenter.

        :raises: VSphereResourceNotFoundError
    """
    if linked is None:
        linked = list_linked_vcenters(client=client, aspects=aspects)

    selected: Optional[LinkedVCenterRecord] = None
    for record in linked:
        if getattr(record, "uuid", None) == uuid:
            selected = record
            break

    if selected is None:
        err_msg_lines = [
            "Linked vCenter UUID is not present in the federation.",
            "UUID: {}".format(uuid),
            "KNOWN UUIDS:",
        ]
        for record in linked:
            err_msg_lines.append("    {}".format(getattr(record, "uuid", "?")))
        err_msg = os.linesep.join(err_msg_lines)
        raise VSphereResourceNotFoundError(err_msg)

    if bool(getattr(selected, "is_local", False)):
        rtnval = client
        return rtnval

    # Deferred import to avoid a circular module dependency between
    # ``vsphereclient`` and this helper.
    from automojo.restclient.vsphere.vsphereclient import VSphereClient

    rtnval = VSphereClient(
        host=selected.hostname,
        credential=client._credential,
        verify_certificate=client._verify_certificate,
    )
    return rtnval


def _build_local_record(*, client: "VSphereClient") -> LinkedVCenterRecord:
    """
        Construct a minimal :class:`LinkedVCenterRecord` describing the
        local vCenter when no peer information is available.

        :param client: The originating client.

        :returns: A :class:`LinkedVCenterRecord` with ``is_local=True``.
    """
    rtnval = LinkedVCenterRecord(
        uuid="local",
        hostname=getattr(client, "_host", "unknown"),
        is_local=True,
    )
    return rtnval
