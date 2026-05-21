"""
    .. module:: ovfgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: OVF API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import os

from http import HTTPStatus
from typing import Optional
from urllib.parse import urlsplit

from automojo.errors.exceptions import SemanticError
from automojo.errors.raising import raise_for_http_status

from automojo.restclient.vsphere.apigroups.basegroup import BaseGroup
from automojo.restclient.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from automojo.restclient.vsphere.model.ovf import OvfDescriptor
from automojo.restclient.vsphere.specs.ovfdeploy import OvfDeploySpec
from automojo.restclient.vsphere.specs.vmplacement import VmPlacementSpec
from automojo.restclient.vsphere.vspheretaskhandle import VSphereTaskHandle


_VALID_URL_SCHEMES = ("http", "https", "file")

# Minimum legitimate OVF/OVA header signature.  OVA files are tar
# archives starting with a filename header in ASCII; OVF descriptors
# are XML and start with ``<?xml`` or ``<Envelope``.
_OVA_TAR_MAGIC = b"ustar"
_OVF_XML_PREFIXES = (b"<?xml", b"<Envelope")


class OvfGroup(BaseGroup):
    """
        OVF operations (``/api/vcenter/ovf``).

        Provides URL-source deploy, local-file (multipart) deploy, and
        descriptor parsing per the ``vsphere-ovf-deploy`` spec.
    """

    BASE_LEAF = "/api/vcenter/ovf"

    DEPLOY_FROM_URL_LEAF = "/api/vcenter/ovf/deploy-from-url"
    DEPLOY_FROM_LOCAL_LEAF = "/api/vcenter/ovf/import"
    PARSE_DESCRIPTOR_LEAF = "/api/vcenter/ovf/parse"

    def parse_descriptor(
        self,
        *,
        source: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> OvfDescriptor:
        """
            Parse an OVF descriptor from a URL or local path.

            :param source: URL or local path.
            :param aspects: Behaviour controls.

            :returns: An :class:`OvfDescriptor`.

            :raises: SemanticError
        """
        client = self.client
        url = client.build_url(leaf=self.PARSE_DESCRIPTOR_LEAF)
        session = client.ensure_session(aspects=aspects)
        body = {"source": source}
        resp = session.post(url, json=body, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            err_msg_lines = [
                "Unable to parse OVF descriptor.",
                "SOURCE: {!r}".format(source),
                "STATUS: {}".format(resp.status_code),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)
        payload = resp.json()
        if not isinstance(payload, dict):
            err_msg_lines = [
                "OVF descriptor response was not an object.",
                "SOURCE: {!r}".format(source),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)
        rtnval = OvfDescriptor.from_dict(payload)
        return rtnval

    def deploy_from_url(
        self,
        *,
        url: str,
        target: VmPlacementSpec,
        deploy_spec: OvfDeploySpec,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Deploy a VM from an OVF/OVA URL.

            :param url: HTTP(S) or file URL.
            :param target: :class:`VmPlacementSpec`.
            :param deploy_spec: :class:`OvfDeploySpec`.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle`.

            :raises: SemanticError
        """
        scheme = urlsplit(url).scheme.lower()
        if scheme not in _VALID_URL_SCHEMES:
            err_msg_lines = [
                "OVF deploy URL scheme not supported.",
                "URL: {!r}".format(url),
                "GOT: {!r}".format(scheme),
                "EXPECTED: one of {}".format(list(_VALID_URL_SCHEMES)),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

        client = self.client
        endpoint = client.build_url(leaf=self.DEPLOY_FROM_URL_LEAF)
        body = {
            "source_url": url,
            "target": target.to_dict(),
            "deployment_spec": deploy_spec.to_dict(),
        }
        session = client.ensure_session(aspects=aspects)
        resp = session.post(endpoint, json=body, timeout=aspects.completion_timeout)
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.CREATED):
            raise_for_http_status(
                resp.status_code, resp.content, endpoint,
                context="OvfGroup.deploy_from_url",
            )
        try:
            response_body = resp.json()
        except ValueError:
            response_body = {}
        task_id = _extract_task_id(payload=response_body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval

    def deploy_from_local_ovf(
        self,
        *,
        ovf_path: str,
        target: VmPlacementSpec,
        deploy_spec: OvfDeploySpec,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereTaskHandle:
        """
            Deploy a VM by uploading a local OVF/OVA via multipart POST.

            :param ovf_path: Absolute filesystem path to the OVF/OVA.
            :param target: :class:`VmPlacementSpec`.
            :param deploy_spec: :class:`OvfDeploySpec`.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereTaskHandle`.

            :raises: FileNotFoundError, SemanticError
        """
        if not os.path.exists(ovf_path):
            err_msg_lines = [
                "Local OVF/OVA path does not exist.",
                "PATH: {!r}".format(ovf_path),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise FileNotFoundError(err_msg)

        _validate_ovf_header(path=ovf_path)

        client = self.client
        endpoint = client.build_url(leaf=self.DEPLOY_FROM_LOCAL_LEAF)

        with open(ovf_path, "rb") as fh:
            file_bytes = fh.read()

        files = {
            "ovf": (os.path.basename(ovf_path), file_bytes, "application/octet-stream"),
        }
        data = {
            "target": _to_json_field(value=target.to_dict()),
            "deployment_spec": _to_json_field(value=deploy_spec.to_dict()),
        }

        session = client.ensure_session(aspects=aspects)
        resp = session.post(
            endpoint, files=files, data=data, timeout=aspects.completion_timeout,
        )
        if resp.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.CREATED):
            raise_for_http_status(
                resp.status_code, resp.content, endpoint,
                context="OvfGroup.deploy_from_local_ovf",
            )
        try:
            response_body = resp.json()
        except ValueError:
            response_body = {}
        task_id = _extract_task_id(payload=response_body)
        rtnval = VSphereTaskHandle(task_id=task_id, client=client)
        return rtnval


def _validate_ovf_header(*, path: str) -> None:
    """
        Cheap header sniff to fail fast on obviously-non-OVF inputs.

        :param path: Filesystem path to the candidate file.

        :returns: ``None``

        :raises: SemanticError
    """
    with open(path, "rb") as fh:
        head = fh.read(512)

    if head.startswith(_OVF_XML_PREFIXES[0]) or head.startswith(_OVF_XML_PREFIXES[1]):
        return None

    # A POSIX tar header places "ustar" at byte 257.
    if len(head) >= 263 and head[257:262] == _OVA_TAR_MAGIC:
        return None

    err_msg_lines = [
        "File at OVF path does not look like a valid OVF or OVA.",
        "PATH: {!r}".format(path),
        "HEAD: {!r}".format(head[:32]),
    ]
    err_msg = os.linesep.join(err_msg_lines)
    raise SemanticError(err_msg)


def _to_json_field(*, value) -> str:
    """
        Render a Python object as a JSON string suitable for a
        multipart text field.

        :param value: The object to serialize.

        :returns: A JSON-encoded string.
    """
    import json

    rtnval = json.dumps(value, sort_keys=True)
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
    rtnval = "" if payload is None else str(payload)
    return rtnval
