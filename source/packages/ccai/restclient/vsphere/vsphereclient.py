"""
    .. module:: vsphereclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Provides :class:`VSphereClient`, a
        :class:`RestClientBase` subclass that replaces the legacy
        ``VSphereAgent`` and exposes 29 lazy-cached API group
        properties.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


import os
import threading
import time

from typing import Any, Dict, Optional

from http import HTTPStatus

from requests import Session
from requests.exceptions import RequestException

from ccai.credentials.basecredential import BaseCredential
from ccai.credentials.basiccredential import BasicCredential

from ccai.errors.exceptions import (
    HttpForbiddenError,
    HttpUnAuthorizedError,
    SemanticError,
)
from ccai.restclient.base.restclientbase import RestClientBase

from ccai.restclient.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from ccai.restclient.vsphere.vspheresession import (
    AUTH_HEADER,
    AUTH_LEAF,
    apply_session_token,
    mint_session_token,
)
from ccai.restclient.vsphere.vspherefilterstate import VSphereFilterState
from ccai.restclient.vsphere.vspherehealth import VSphereHealth


_API_PREFIX = "/api/"
_REST_PREFIX = "/rest/"


_GROUP_REGISTRY = (
    ("CertificateManagement",
        "ccai.restclient.vsphere.apigroups.certificatemanagementgroup",
        "CertificateManagementGroup"),
    ("Cluster",
        "ccai.restclient.vsphere.apigroups.clustergroup",
        "ClusterGroup"),
    ("Compute",
        "ccai.restclient.vsphere.apigroups.computegroup",
        "ComputeGroup"),
    ("Content",
        "ccai.restclient.vsphere.apigroups.contentgroup",
        "ContentGroup"),
    ("CryptoManager",
        "ccai.restclient.vsphere.apigroups.cryptomanagergroup",
        "CryptoManagerGroup"),
    ("Datacenter",
        "ccai.restclient.vsphere.apigroups.datacentergroup",
        "DatacenterGroup"),
    ("Datastore",
        "ccai.restclient.vsphere.apigroups.datastoregroup",
        "DatastoreGroup"),
    ("Deployment",
        "ccai.restclient.vsphere.apigroups.deploymentgroup",
        "DeploymentGroup"),
    ("Events",
        "ccai.restclient.vsphere.apigroups.eventsgroup",
        "EventsGroup"),
    ("Folder",
        "ccai.restclient.vsphere.apigroups.foldergroup",
        "FolderGroup"),
    ("Guest",
        "ccai.restclient.vsphere.apigroups.guestgroup",
        "GuestGroup"),
    ("Host",
        "ccai.restclient.vsphere.apigroups.hostgroup",
        "HostGroup"),
    ("Hvc",
        "ccai.restclient.vsphere.apigroups.hvcgroup",
        "HvcGroup"),
    ("Identity",
        "ccai.restclient.vsphere.apigroups.identitygroup",
        "IdentityGroup"),
    ("Inventory",
        "ccai.restclient.vsphere.apigroups.inventorygroup",
        "InventoryGroup"),
    ("Iso",
        "ccai.restclient.vsphere.apigroups.isogroup",
        "IsoGroup"),
    ("Lcm",
        "ccai.restclient.vsphere.apigroups.lcmgroup",
        "LcmGroup"),
    ("NamespaceManagement",
        "ccai.restclient.vsphere.apigroups.namespacemanagementgroup",
        "NamespaceManagementGroup"),
    ("Namespaces",
        "ccai.restclient.vsphere.apigroups.namespacesgroup",
        "NamespacesGroup"),
    ("Network",
        "ccai.restclient.vsphere.apigroups.networkgroup",
        "NetworkGroup"),
    ("Ovf",
        "ccai.restclient.vsphere.apigroups.ovfgroup",
        "OvfGroup"),
    ("ResourcePool",
        "ccai.restclient.vsphere.apigroups.resourcepoolgroup",
        "ResourcePoolGroup"),
    ("Services",
        "ccai.restclient.vsphere.apigroups.servicesgroup",
        "ServicesGroup"),
    ("Storage",
        "ccai.restclient.vsphere.apigroups.storagegroup",
        "StorageGroup"),
    ("SystemConfig",
        "ccai.restclient.vsphere.apigroups.systemconfiggroup",
        "SystemConfigGroup"),
    ("Tagging",
        "ccai.restclient.vsphere.apigroups.tagginggroup",
        "TaggingGroup"),
    ("TokenService",
        "ccai.restclient.vsphere.apigroups.tokenservicegroup",
        "TokenServiceGroup"),
    ("Topology",
        "ccai.restclient.vsphere.apigroups.topologygroup",
        "TopologyGroup"),
    ("TrustedInfrastructure",
        "ccai.restclient.vsphere.apigroups.trustedinfrastructuregroup",
        "TrustedInfrastructureGroup"),
    ("Vm",
        "ccai.restclient.vsphere.apigroups.vmgroup",
        "VmGroup"),
)


# Aliases for landscape-compat property names.  The legacy
# ``VSphereAgent`` used ``DataCenter`` and ``DataStore`` (mixed-case
# inner "C" / "S").  The spec spells them ``Datacenter`` and
# ``Datastore``.  We register the canonical name with the lazy cache
# and expose the legacy spelling as a thin alias so existing call
# sites keep working.
_LEGACY_ALIASES = {
    "DataCenter": "Datacenter",
    "DataStore": "Datastore",
}


class VSphereClient(RestClientBase):
    """
        :class:`RestClientBase` subclass for vSphere.

        Builds the host URL once at construction time, exposes the 29
        API groups as lazy-cached properties matching the legacy
        ``VSphereAgent`` naming convention, and overrides
        :meth:`authenticate` to perform vSphere's session-token
        exchange instead of the default basic-auth dance.
    """

    AUTH_LEAF = AUTH_LEAF

    # vSphere lab environments commonly use self-signed certs.  The
    # caller can override this per-instance, but the default mirrors
    # the legacy agent's posture.
    VERIFY_CERTIFICATE = False

    # Re-authenticate transparently when the session is rejected.
    AUTHENTICATION_FAILURES = (HttpForbiddenError, HttpUnAuthorizedError)

    def __init__(
        self,
        *,
        host: str,
        credential: BaseCredential,
        port: Optional[int] = None,
        scheme: str = "https",
        headers: Optional[Dict[str, str]] = None,
        verify_certificate: Optional[bool] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> None:
        """
            Construct a :class:`VSphereClient`.

            :param host: Hostname or IP of the vCenter server.
            :param credential: A :class:`BasicCredential` carrying
                username / password.
            :param port: Optional non-default port.
            :param scheme: URL scheme, default ``https``.
            :param headers: Optional default headers.
            :param verify_certificate: Override TLS verification.
            :param aspects: Default :class:`AspectsVSphere` instance.

            :returns: ``None``

            :raises: SemanticError
        """
        if not isinstance(credential, BasicCredential):
            err_msg_lines = [
                "VSphereClient requires a BasicCredential.",
                "GOT: {}".format(type(credential).__name__),
                "EXPECTED: BasicCredential (or compatible subclass)",
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

        super().__init__(
            host=host,
            credential=credential,
            port=port,
            scheme=scheme,
            headers=headers,
            verify_certificate=verify_certificate,
            aspects=aspects,
        )

        self._filter_state = VSphereFilterState()
        self._group_cache: Dict[str, Any] = {}
        self._auth_lock = threading.Lock()
        self._auth_token: Optional[str] = None
        return

    # ------------------------------------------------------------------
    # URL composition
    # ------------------------------------------------------------------

    def build_url(self, *, leaf: str) -> str:
        """
            Compose an absolute URL for a leaf that already starts with
            either ``/api/`` or ``/rest/``.

            :param leaf: Leaf path beginning with one of the recognised
                root prefixes.

            :returns: The absolute URL.

            :raises: SemanticError
        """
        self._validate_leaf_prefix(leaf=leaf)
        rtnval = "{}{}".format(self._host_url, leaf)
        return rtnval

    def build_api_url(self, *, leaf: str) -> str:
        """
            Compose an absolute URL under the ``/api/`` root.

            :param leaf: Path beneath ``/api`` (with or without the
                leading ``/api`` prefix).

            :returns: The absolute URL.
        """
        if leaf.startswith(_API_PREFIX):
            normalized = leaf
        elif leaf.startswith("/"):
            normalized = "/api" + leaf
        else:
            normalized = "/api/" + leaf
        rtnval = "{}{}".format(self._host_url, normalized)
        return rtnval

    def build_rest_url(self, *, leaf: str) -> str:
        """
            Compose an absolute URL under the ``/rest/`` root.

            :param leaf: Path beneath ``/rest`` (with or without the
                leading ``/rest`` prefix).

            :returns: The absolute URL.
        """
        if leaf.startswith(_REST_PREFIX):
            normalized = leaf
        elif leaf.startswith("/"):
            normalized = "/rest" + leaf
        else:
            normalized = "/rest/" + leaf
        rtnval = "{}{}".format(self._host_url, normalized)
        return rtnval

    @staticmethod
    def _validate_leaf_prefix(*, leaf: str) -> None:
        """
            Ensures a leaf begins with ``/api/`` or ``/rest/``.

            :param leaf: Candidate leaf path.

            :returns: ``None``

            :raises: SemanticError
        """
        if leaf.startswith(_API_PREFIX):
            return None
        if leaf.startswith(_REST_PREFIX):
            return None

        err_msg_lines = [
            "VSphere leaf must begin with '/api/' or '/rest/'.",
            "GOT: {!r}".format(leaf),
        ]
        err_msg = os.linesep.join(err_msg_lines)
        raise SemanticError(err_msg)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        """
            Override of :meth:`RestClientBase.authenticate` that
            performs the vSphere session-token mint.

            :returns: ``None``
        """
        with self._auth_lock:
            session = Session()
            session.verify = self._verify_certificate

            token = mint_session_token(
                session=session,
                base_url=self._host_url,
                credential=self._credential,
                verify_certificate=self._verify_certificate,
            )
            apply_session_token(session=session, token=token)

            self._session = session
            self._auth_token = token
        return None

    def ensure_session(self, *, aspects: AspectsVSphere) -> Session:
        """
            Returns the active requests session, minting one on first
            use.

            :param aspects: Behaviour controls (carried for symmetry
                with the rest of the public surface).

            :returns: The :class:`requests.Session` currently bound to
                this client.
        """
        _ = aspects
        if self._session is None:
            self.authenticate()
        rtnval = self._session
        return rtnval

    @property
    def auth_token(self) -> Optional[str]:
        """
            Cached session id, or ``None`` before first authentication.

            :returns: The token string or ``None``.
        """
        rtnval = self._auth_token
        return rtnval

    # ------------------------------------------------------------------
    # Filter state
    # ------------------------------------------------------------------

    @property
    def filter_state(self) -> VSphereFilterState:
        """
            Active :class:`VSphereFilterState`.

            :returns: The current filter state instance.
        """
        rtnval = self._filter_state
        return rtnval

    def set_filter_state(
        self,
        *,
        datacenter: Optional[str] = None,
        folder: Optional[str] = None,
        cluster: Optional[str] = None,
        resource_pool: Optional[str] = None,
    ) -> None:
        """
            Replace the active filter state.

            :param datacenter: Working datacenter id.
            :param folder: Working folder id.
            :param cluster: Working cluster id.
            :param resource_pool: Working resource pool id.

            :returns: ``None``
        """
        self._filter_state = VSphereFilterState(
            datacenter=datacenter,
            folder=folder,
            cluster=cluster,
            resource_pool=resource_pool,
        )
        return None

    def clear_filter_state(self) -> None:
        """
            Reset the filter state to the empty default.

            :returns: ``None``
        """
        self._filter_state = VSphereFilterState()
        return None

    # ------------------------------------------------------------------
    # Health probe
    # ------------------------------------------------------------------

    def health(
        self,
        *,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VSphereHealth:
        """
            Probe vCenter reachability and session validity.

            :param aspects: Behaviour controls for the probe.

            :returns: A :class:`VSphereHealth` snapshot.
        """
        reachable = False
        session_valid = False
        time_skew = 0.0

        try:
            session = self.ensure_session(aspects=aspects)
            probe_url = self.build_api_url(leaf="/api/appliance/system/version")
            client_clock = time.time()
            resp = session.get(probe_url, timeout=aspects.completion_timeout)
            reachable = True
            if resp.status_code == HTTPStatus.OK:
                session_valid = True
            elif resp.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                session_valid = False
            date_header = resp.headers.get("Date")
            if date_header is not None:
                # Best-effort skew estimate; we keep it as 0.0 unless we
                # can compute it.  The Date header parse is intentionally
                # left for a downstream enhancement so a malformed value
                # does not cause health() to raise.
                _ = client_clock
                time_skew = 0.0
        except RequestException:
            reachable = False
            session_valid = False
            time_skew = 0.0

        rtnval = VSphereHealth(
            reachable=reachable,
            session_valid=session_valid,
            time_skew_seconds=time_skew,
        )
        return rtnval

    # ------------------------------------------------------------------
    # Linked Mode (HVC) helpers
    # ------------------------------------------------------------------

    def linked_vcenters(
        self,
        *,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ):
        """
            Enumerate vCenters federated with this client via Linked
            Mode (Hybrid Linked Mode).

            When linked mode is not configured the result is a
            single-entry list containing only the local vCenter.

            :param aspects: Behaviour controls.

            :returns: List of :class:`LinkedVCenterRecord`.
        """
        # Deferred import avoids a circular dependency between this
        # module and ``linkedmode``.
        from ccai.restclient.vsphere.linkedmode import list_linked_vcenters

        rtnval = list_linked_vcenters(client=self, aspects=aspects)
        return rtnval

    def for_vcenter(
        self,
        *,
        uuid: str,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> "VSphereClient":
        """
            Return a :class:`VSphereClient` scoped to a specific linked
            vCenter.

            :param uuid: Target vCenter UUID.
            :param aspects: Behaviour controls.

            :returns: A :class:`VSphereClient`.

            :raises: VSphereResourceNotFoundError
        """
        from ccai.restclient.vsphere.linkedmode import build_scoped_client

        rtnval = build_scoped_client(client=self, uuid=uuid, aspects=aspects)
        return rtnval

    # ------------------------------------------------------------------
    # API group access
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """
            Lazy-cached property access for API groups.

            Triggered when normal attribute lookup misses; we look the
            name up in the group registry, import the module, construct
            the group, and cache it.

            :param name: Attribute name being accessed.

            :returns: The cached group instance.

            :raises: AttributeError
        """
        canonical_name = _LEGACY_ALIASES.get(name, name)

        cache = self.__dict__.get("_group_cache")
        if cache is None:
            # ``__getattr__`` is being called during partial
            # initialisation; defer to standard lookup.
            err_msg = "{!r} object has no attribute {!r}".format(
                type(self).__name__, name,
            )
            raise AttributeError(err_msg)

        if canonical_name in cache:
            rtnval = cache[canonical_name]
            return rtnval

        for entry_name, module_path, class_name in _GROUP_REGISTRY:
            if entry_name == canonical_name:
                module = __import__(module_path, fromlist=[class_name])
                group_class = getattr(module, class_name)
                instance = group_class(self)
                cache[canonical_name] = instance
                rtnval = instance
                return rtnval

        available = sorted(entry[0] for entry in _GROUP_REGISTRY)
        err_msg_lines = [
            "VSphereClient has no API group named {!r}.".format(name),
            "AVAILABLE GROUPS:",
        ]
        for grp in available:
            err_msg_lines.append("    {}".format(grp))
        err_msg = os.linesep.join(err_msg_lines)
        raise AttributeError(err_msg)
