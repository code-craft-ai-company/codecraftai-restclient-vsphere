"""
    .. module:: vspheresession
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Session-token mint/refresh helpers, separated so they
        can be unit-tested without the full :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import os

from http import HTTPStatus

from requests import Session, Response

from automojo.credentials.basiccredential import BasicCredential
from automojo.errors.exceptions import HttpForbiddenError


AUTH_HEADER = "vmware-api-session-id"
AUTH_LEAF = "/rest/com/vmware/cis/session"


def mint_session_token(
    *,
    session: Session,
    base_url: str,
    credential: BasicCredential,
    verify_certificate: bool,
) -> str:
    """
        POST credentials to the vSphere session endpoint and return the
        minted session token string.

        :param session: An open :class:`requests.Session` to POST on.
        :param base_url: The host URL (e.g. ``https://vc.example.com``).
        :param credential: Username / password credential.
        :param verify_certificate: TLS verification flag.

        :returns: The minted session id (the ``value`` field of the
            response).

        :raises: HttpForbiddenError
    """
    auth_url = "{}{}".format(base_url.rstrip("/"), AUTH_LEAF)

    resp: Response = session.post(
        auth_url,
        auth=(credential.username, credential.password),
        verify=verify_certificate,
    )

    status_code = resp.status_code
    if status_code != HTTPStatus.OK:
        err_msg_lines = [
            "Failed to mint vSphere session token.",
            "URL: {}".format(auth_url),
            "STATUS: {}".format(status_code),
            "BODY: {!r}".format(resp.content),
        ]
        err_msg = os.linesep.join(err_msg_lines)
        raise HttpForbiddenError(err_msg)

    payload = resp.json()
    token = payload.get("value")
    if token is None:
        err_msg_lines = [
            "vSphere session response missing 'value' field.",
            "URL: {}".format(auth_url),
            "BODY: {!r}".format(payload),
        ]
        err_msg = os.linesep.join(err_msg_lines)
        raise HttpForbiddenError(err_msg)

    rtnval = token
    return rtnval


def apply_session_token(*, session: Session, token: str) -> None:
    """
        Install a minted session token on the session's default
        headers so every subsequent request carries it.

        :param session: The session to mutate.
        :param token: The session id string.

        :returns: ``None``
    """
    session.headers[AUTH_HEADER] = token
    return None
