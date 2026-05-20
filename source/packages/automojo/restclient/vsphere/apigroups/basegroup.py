"""
    .. module:: basegroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Shared base class for every vSphere ``*Group`` API
        surface.  Adds filter-state-aware URL composition on top of the
        generic :class:`RestApiGroup`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import os

from typing import TYPE_CHECKING

from automojo.errors.exceptions import SemanticError
from automojo.restclient.base.restapigroup import RestApiGroup


if TYPE_CHECKING:
    from automojo.restclient.vsphere.vsphereclient import VSphereClient


_API_PREFIX = "/api/"
_REST_PREFIX = "/rest/"


class BaseGroup(RestApiGroup):
    """
        Common ancestor for every vSphere API group.

        Subclasses MUST set :data:`BASE_LEAF` to a value that begins
        with either ``/api/`` or ``/rest/`` so the client knows which
        root to compose against.  The prefix is validated at subclass
        registration time (``__init_subclass__``) so misconfiguration
        fails fast.
    """

    BASE_LEAF: str = ""

    def __init_subclass__(cls, **kwargs) -> None:
        """
            Validate ``BASE_LEAF`` of subclasses at class-definition
            time.

            :returns: ``None``

            :raises: SemanticError
        """
        super().__init_subclass__(**kwargs)
        # An empty BASE_LEAF is permitted only on the base class itself
        # which is the class statically declared in this module.
        if cls is BaseGroup:
            return None

        base = cls.BASE_LEAF
        if base is None or len(base) == 0:
            err_msg_lines = [
                "API group must declare a non-empty BASE_LEAF.",
                "CLASS: {}".format(cls.__name__),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

        if not (base.startswith(_API_PREFIX) or base.startswith(_REST_PREFIX)):
            err_msg_lines = [
                "API group BASE_LEAF must begin with '/api/' or '/rest/'.",
                "CLASS: {}".format(cls.__name__),
                "GOT: {!r}".format(base),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

        return None

    def __init__(self, client: "VSphereClient") -> None:
        """
            Initialise the group with a back-reference to the client.

            :param client: Owning :class:`VSphereClient` instance.

            :returns: ``None``
        """
        super().__init__(client)
        return

    # ------------------------------------------------------------------
    # URL composition wrapped over RestApiGroup.build_leaf
    # ------------------------------------------------------------------

    def compose_url(self, *, parts=None, params=None) -> str:
        """
            Compose an absolute URL by joining BASE_LEAF with any
            additional path parts.

            Query parameters are not embedded into the returned URL;
            they are emitted via the `params=` argument to requests in
            sorted-key order.  The sort key ordering invariant is
            enforced at the call site (e.g. the ``params`` dict passed
            to ``session.get``) so the property-test suite need not
            inspect raw URLs.

            :param parts: Optional list of additional path segments
                to append after BASE_LEAF.
            :param params: Optional dict of query parameters (forwarded
                to callers; not embedded into the URL string here).

            :returns: The absolute URL composed against the client.
        """
        _ = params
        client = self.client
        if parts is None or len(parts) == 0:
            leaf = self.BASE_LEAF
        else:
            leaf = self.build_leaf(parts=parts)
            if not leaf.startswith("/"):
                leaf = "/" + leaf

        rtnval = client.build_url(leaf=leaf)
        return rtnval

    def sort_params(self, *, params) -> dict:
        """
            Return the params dict re-keyed alphabetically.

            :param params: Raw params dict (may be ``None``).

            :returns: A new dict with keys in sorted order.
        """
        rtnval = {}
        if params is None:
            return rtnval
        for key in sorted(params.keys()):
            rtnval[key] = params[key]
        return rtnval
