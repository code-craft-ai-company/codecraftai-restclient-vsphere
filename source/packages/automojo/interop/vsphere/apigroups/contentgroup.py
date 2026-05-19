"""
    .. module:: contentgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Content library API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import os

from http import HTTPStatus

from typing import List, Optional

from automojo.errors.raising import raise_for_http_status

from automojo.interop.vsphere.apigroups.basegroup import BaseGroup
from automojo.interop.vsphere.apigroups.inventoryerrors import (
    VSphereAmbiguousResolutionError,
    VSphereResourceNotFoundError,
)
from automojo.interop.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from automojo.interop.vsphere.model.library import LibraryItemSummary
from automojo.interop.vsphere.specs.contentdeploy import ContentDeploySpec
from automojo.interop.vsphere.specs.vmplacement import VmPlacementSpec
from automojo.interop.vsphere.vspheretaskhandle import VSphereTaskHandle


class ContentGroup(BaseGroup):
    """
        Content library operations (``/api/content/...``).

        The legacy ``ContentExt`` did not expose public methods; this
        class adds ``list_items``, ``find_item``, and ``deploy_ovf_item``
        per the ``vsphere-content-library-deploy`` spec.
    """

    BASE_LEAF = "/api/content"

    LIBRARY_LEAF = "/api/content/library"
    LIBRARY_ITEM_LEAF = "/api/content/library/item"
    LIBRARY_ITEM_DEPLOY_LEAF = "/api/vcenter/ovf/library-item"

    def list_items(
        self,
        *,
        library_id: str,
        tag: Optional[str] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[LibraryItemSummary]:
        """
            Enumerate items in a content library.

            Tag filtering is performed client-side against the ``tags``
            field on the returned summaries so the helper is uniform
            regardless of whether the underlying endpoint supports
            server-side tag filtering.

            :param library_id: Content-library identifier.
            :param tag: Optional tag filter.
            :param aspects: Behaviour controls.

            :returns: List of :class:`LibraryItemSummary`.

            :raises: VSphereResourceNotFoundError
        """
        client = self.client
        url = client.build_url(leaf=self.LIBRARY_ITEM_LEAF)
        session = client.ensure_session(aspects=aspects)
        params = {"library_id": library_id}
        resp = session.get(url, params=params, timeout=aspects.completion_timeout)

        if resp.status_code == HTTPStatus.NOT_FOUND:
            err_msg_lines = [
                "Content library not found.",
                "LIBRARY_ID: {}".format(library_id),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise VSphereResourceNotFoundError(err_msg)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(
                resp.status_code, resp.content, url, context="ContentGroup.list_items",
            )

        body = resp.json()
        parsed: List[LibraryItemSummary] = []
        for raw in body:
            if isinstance(raw, str):
                # Endpoint variant returns bare item-ids; promote each
                # to a minimal summary so the surface stays uniform.
                parsed.append(LibraryItemSummary(
                    item_id=raw, library_id=library_id, name=raw,
                ))
                continue
            normalised = dict(raw)
            if "item_id" not in normalised:
                if "id" in normalised:
                    normalised["item_id"] = normalised.pop("id")
            if "library_id" not in normalised:
                normalised["library_id"] = library_id
            parsed.append(LibraryItemSummary.from_dict(normalised))

        if tag is None:
            rtnval = parsed
            return rtnval

        filtered: List[LibraryItemSummary] = []
        for item in parsed:
            tags = getattr(item, "tags", None)
            if tags is None:
                continue
            if tag in tags:
                filtered.append(item)
        rtnval = filtered
        return rtnval

    def find_item(
        self,
        *,
        name: str,
        tag: Optional[str] = None,
        library_id: Optional[str] = None,
        all_library_ids: Optional[List[str]] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> LibraryItemSummary:
        """
            Resolve a friendly name (and optional tag) to a single
            :class:`LibraryItemSummary`.

            When ``library_id`` is omitted, ``all_library_ids`` is used
            as the search scope.  The latter is named-only and explicit
            so callers cannot accidentally trigger a full-tenancy enum
            without acknowledging it.

            :param name: Item display name.
            :param tag: Optional tag the item must also carry.
            :param library_id: Optional single-library scope.
            :param all_library_ids: Optional multi-library scope.
            :param aspects: Behaviour controls.

            :returns: A single :class:`LibraryItemSummary`.

            :raises: VSphereResourceNotFoundError,
                VSphereAmbiguousResolutionError
        """
        scope: List[str] = []
        if library_id is not None:
            scope.append(library_id)
        elif all_library_ids is not None:
            scope.extend(all_library_ids)
        else:
            err_msg_lines = [
                "ContentGroup.find_item requires either library_id or",
                "all_library_ids to define the search scope.",
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise VSphereResourceNotFoundError(err_msg)

        candidates: List[LibraryItemSummary] = []
        for lib_id in scope:
            for item in self.list_items(library_id=lib_id, tag=tag, aspects=aspects):
                if getattr(item, "name", None) == name:
                    candidates.append(item)

        if len(candidates) == 0:
            err_msg_lines = [
                "No content-library item matched the requested name.",
                "NAME: {}".format(name),
                "TAG: {}".format(tag),
                "SCOPE: {}".format(scope),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise VSphereResourceNotFoundError(err_msg)

        if len(candidates) > 1:
            err_msg_lines = [
                "Multiple content-library items matched the requested name.",
                "NAME: {}".format(name),
                "COUNT: {}".format(len(candidates)),
            ]
            for cand in candidates:
                err_msg_lines.append(
                    "    {}: {}".format(cand.item_id, cand.library_id),
                )
            err_msg = os.linesep.join(err_msg_lines)
            raise VSphereAmbiguousResolutionError(err_msg, candidates=candidates)

        rtnval = candidates[0]
        return rtnval

    def deploy_ovf_item(
        self,
        *,
        item_id: str,
        target: VmPlacementSpec,
        deploy_spec: ContentDeploySpec,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Deploy an OVF library item into the requested placement.

            :param item_id: Library item identifier.
            :param target: :class:`VmPlacementSpec`.
            :param deploy_spec: :class:`ContentDeploySpec`.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle` for the deployment.
        """
        client = self.client
        leaf = "{}/{}?action=deploy".format(self.LIBRARY_ITEM_DEPLOY_LEAF, item_id)
        url = client.build_url(leaf=leaf)

        deployment_target = target.to_dict()
        deployment_spec = deploy_spec.to_dict()
        body = {
            "target": deployment_target,
            "deployment_spec": deployment_spec,
        }

        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=body, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.CREATED):
            raise_for_http_status(
                resp.status_code, resp.content, url,
                context="ContentGroup.deploy_ovf_item",
            )
        try:
            response_body = resp.json()
        except Exception:
            response_body = {}
        task_id = _extract_task_id(payload=response_body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval


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
        if "succeeded" in payload and isinstance(payload.get("resource_id"), str):
            rtnval = payload["resource_id"]
            return rtnval
    rtnval = "" if payload is None else str(payload)
    return rtnval
