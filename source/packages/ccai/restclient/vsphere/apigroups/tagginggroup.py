"""
    .. module:: tagginggroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Tagging API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import List, Optional

from http import HTTPStatus

from ccai.errors.raising import raise_for_http_status

from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup
from ccai.restclient.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)


_CATEGORY_LEAF = "/api/cis/tagging/category"
_ASSOCIATION_LEAF = "/api/cis/tagging/tag-association"


def _unwrap(*, payload):
    """
        Unwrap a vCenter tagging response that may nest its data under a
        ``value`` key (the ``/rest`` legacy envelope) or return it bare
        (the ``/api`` surface).

        :param payload: The decoded JSON body.

        :returns: The unwrapped value.
    """
    if isinstance(payload, dict) and "value" in payload:
        rtnval = payload["value"]
        return rtnval
    rtnval = payload
    return rtnval


class TaggingGroup(BaseGroup):
    """
        Tagging operations (``/api/cis/tagging``).

        Covers category discovery / creation, the tag-attach and
        tag-detach association surface, and the reverse-lookup helpers
        the cloud-provisioning venue needs to enforce idempotent
        tag-driven cleanup.
    """

    BASE_LEAF = "/api/cis/tagging"

    def ensure_category(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        cardinality: str = "MULTIPLE",
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> str:
        """
            Return the id of a category with ``name``, creating it when
            it does not already exist.

            :param name: Category display name.
            :param description: Optional category description used only
                when the category is created.
            :param cardinality: ``SINGLE`` or ``MULTIPLE``; used only
                when the category is created.
            :param aspects: Behaviour controls.

            :returns: The category identifier.
        """
        existing = self._find_category_id_by_name(name=name, aspects=aspects)
        if existing is not None:
            rtnval = existing
            return rtnval

        client = self.client
        url = client.build_url(leaf=_CATEGORY_LEAF)
        spec = {
            "name": name,
            "cardinality": cardinality,
            "associable_types": [],
        }
        if description is not None:
            spec["description"] = description
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json={"create_spec": spec}, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.CREATED):
            raise_for_http_status(resp.status_code, resp.content, url, context="TaggingGroup.ensure_category")
        body = _unwrap(payload=resp.json())
        rtnval = body if isinstance(body, str) else str(body)
        return rtnval

    def attach_tag(
        self,
        *,
        tag_id: str,
        object_type: str,
        object_id: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> None:
        """
            Attach a tag to a managed object.

            :param tag_id: Tag identifier.
            :param object_type: vCenter object type, e.g. ``VirtualMachine``.
            :param object_id: Managed object identifier.
            :param aspects: Behaviour controls.

            :returns: ``None``
        """
        client = self.client
        url = client.build_url(
            leaf="{}/id:{}?action=attach".format(_ASSOCIATION_LEAF, tag_id)
        )
        payload = {"object_id": {"type": object_type, "id": object_id}}
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=payload, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            raise_for_http_status(resp.status_code, resp.content, url, context="TaggingGroup.attach_tag")
        return None

    def detach_tag(
        self,
        *,
        tag_id: str,
        object_type: str,
        object_id: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> None:
        """
            Detach a tag from a managed object.

            :param tag_id: Tag identifier.
            :param object_type: vCenter object type, e.g. ``VirtualMachine``.
            :param object_id: Managed object identifier.
            :param aspects: Behaviour controls.

            :returns: ``None``
        """
        client = self.client
        url = client.build_url(
            leaf="{}/id:{}?action=detach".format(_ASSOCIATION_LEAF, tag_id)
        )
        payload = {"object_id": {"type": object_type, "id": object_id}}
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=payload, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            raise_for_http_status(resp.status_code, resp.content, url, context="TaggingGroup.detach_tag")
        return None

    def list_attached_objects(
        self,
        *,
        tag_id: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[dict]:
        """
            List the managed objects a tag is attached to.

            :param tag_id: Tag identifier.
            :param aspects: Behaviour controls.

            :returns: A list of ``{"type": ..., "id": ...}`` dicts.
        """
        client = self.client
        url = client.build_url(
            leaf="{}/id:{}?action=list-attached-objects".format(
                _ASSOCIATION_LEAF, tag_id
            )
        )
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="TaggingGroup.list_attached_objects")
        body = _unwrap(payload=resp.json())
        rtnval = list(body) if body is not None else []
        return rtnval

    def list_attached_tags(
        self,
        *,
        object_type: str,
        object_id: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[str]:
        """
            List the tag ids attached to a managed object.

            :param object_type: vCenter object type, e.g. ``VirtualMachine``.
            :param object_id: Managed object identifier.
            :param aspects: Behaviour controls.

            :returns: A list of tag identifiers.
        """
        client = self.client
        url = client.build_url(
            leaf="{}?action=list-attached-tags".format(_ASSOCIATION_LEAF)
        )
        payload = {"object_id": {"type": object_type, "id": object_id}}
        session = client.ensure_session(aspects=aspects)
        resp = session.post(url, json=payload, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(resp.status_code, resp.content, url, context="TaggingGroup.list_attached_tags")
        body = _unwrap(payload=resp.json())
        rtnval = list(body) if body is not None else []
        return rtnval

    def _find_category_id_by_name(
        self,
        *,
        name: str,
        aspects: AspectsVSphere,
    ) -> Optional[str]:
        """
            Resolve the id of a category by display name.

            :param name: Category display name.
            :param aspects: Behaviour controls.

            :returns: The category identifier, or ``None`` when no
                category carries ``name``.
        """
        client = self.client
        list_url = client.build_url(leaf=_CATEGORY_LEAF)
        session = client.ensure_session(aspects=aspects)
        list_resp = session.get(list_url, timeout=aspects.completion_timeout)
        if list_resp.status_code != HTTPStatus.OK:
            raise_for_http_status(list_resp.status_code, list_resp.content, list_url, context="TaggingGroup.ensure_category")
        category_ids = _unwrap(payload=list_resp.json())

        found = None
        if category_ids is not None:
            for category_id in category_ids:
                detail_url = client.build_url(
                    leaf="{}/id:{}".format(_CATEGORY_LEAF, category_id)
                )
                detail_resp = session.get(detail_url, timeout=aspects.completion_timeout)
                if detail_resp.status_code != HTTPStatus.OK:
                    raise_for_http_status(detail_resp.status_code, detail_resp.content, detail_url, context="TaggingGroup.ensure_category")
                detail = _unwrap(payload=detail_resp.json())
                if isinstance(detail, dict) and detail.get("name") == name:
                    found = category_id
                    break

        rtnval = found
        return rtnval
