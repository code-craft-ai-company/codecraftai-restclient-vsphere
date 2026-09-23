"""
    Tests for :class:`VSphereClient`: construction, URL composition,
    property-based group access, filter state, authentication, and
    session renewal.
"""

from unittest.mock import MagicMock, patch

from ccai import testbase

from ccai.credentials.basiccredential import BasicCredential
from ccai.errors.exceptions import SemanticError

from ccai.restclient.vsphere.vsphereclient import VSphereClient
from ccai.restclient.vsphere.vspheresession import AUTH_HEADER


def _make_credential() -> BasicCredential:
    rtnval = BasicCredential(
        identifier="vc-login",
        categories=["basic"],
        username="administrator@vsphere.local",
        password="hunter2",
    )
    return rtnval


def _make_client() -> VSphereClient:
    """
        Builds the client the url-composition, group-access and
        filter-state tests share.  This was a ``setUp`` method before
        these tests were expressed as testbase functions.

        :returns: A :class:`VSphereClient` for 'vc.example.com'.
    """
    rtnval = VSphereClient(host="vc.example.com", credential=_make_credential())
    return rtnval


# ----------------------------------------------------------------------
# TestVSphereClientConstruction
# ----------------------------------------------------------------------


def test_construct_with_basic_credential() -> None:
    client = VSphereClient(host="vc.example.com", credential=_make_credential())
    testbase.assert_equal(client.host, "vc.example.com")
    testbase.assert_true(client.auth_token is None)
    return


def test_construct_with_wrong_credential_type_raises_semantic() -> None:
    bad = MagicMock(spec=object)
    with testbase.raises(SemanticError):
        VSphereClient(host="vc.example.com", credential=bad)
    return


def test_no_io_on_construct() -> None:
    # Patch Session at the module level used by the session-mint
    # helper.  If construction issues network I/O, this would be
    # called.
    with patch("ccai.restclient.vsphere.vsphereclient.Session") as session_cls:
        client = VSphereClient(host="vc.example.com", credential=_make_credential())
        testbase.assert_equal(session_cls.call_count, 0)
        _ = client
    return


# ----------------------------------------------------------------------
# TestVSphereClientUrlComposition
# ----------------------------------------------------------------------


def test_build_url_accepts_api_prefix() -> None:
    client = _make_client()
    url = client.build_url(leaf="/api/vcenter/vm")
    testbase.assert_equal(url, "https://vc.example.com/api/vcenter/vm")
    return


def test_build_url_accepts_rest_prefix() -> None:
    client = _make_client()
    url = client.build_url(leaf="/rest/com/vmware/cis/session")
    testbase.assert_equal(url, "https://vc.example.com/rest/com/vmware/cis/session")
    return


def test_build_url_rejects_unknown_prefix() -> None:
    client = _make_client()
    with testbase.raises(SemanticError):
        client.build_url(leaf="/legacy/no/prefix")
    return


def test_build_api_url_normalizes() -> None:
    client = _make_client()
    url = client.build_api_url(leaf="/vcenter/datacenter")
    testbase.assert_equal(url, "https://vc.example.com/api/vcenter/datacenter")
    return


def test_build_rest_url_normalizes() -> None:
    client = _make_client()
    url = client.build_rest_url(leaf="/com/vmware/cis/session")
    testbase.assert_equal(url, "https://vc.example.com/rest/com/vmware/cis/session")
    return


# ----------------------------------------------------------------------
# TestVSphereClientGroupAccess
# ----------------------------------------------------------------------


def test_vm_group_property_returns_vmgroup() -> None:
    from ccai.restclient.vsphere.apigroups.vmgroup import VmGroup

    client = _make_client()
    vm = client.Vm
    testbase.assert_true(isinstance(vm, VmGroup))
    return


def test_group_property_is_cached_identity() -> None:
    client = _make_client()
    first = client.Vm
    second = client.Vm
    testbase.assert_true(first is second)
    return


def test_legacy_alias_resolves_to_canonical() -> None:
    client = _make_client()
    canonical = client.Datacenter
    legacy = client.DataCenter
    testbase.assert_true(canonical is legacy)
    return


def test_unknown_group_raises_attributeerror() -> None:
    client = _make_client()
    with testbase.raises(AttributeError) as ctx:
        _ = client.NoSuchGroup
    # Helpful message must list available groups.
    message = str(ctx.exception)
    testbase.assert_true("AVAILABLE GROUPS" in message)
    testbase.assert_true("Vm" in message)
    return


# ----------------------------------------------------------------------
# TestVSphereClientFilterState
# ----------------------------------------------------------------------


def test_initial_filter_state_is_empty() -> None:
    client = _make_client()
    testbase.assert_true(client.filter_state.is_empty())
    return


def test_set_filter_state() -> None:
    client = _make_client()
    client.set_filter_state(datacenter="dc-1", folder="folder-1")
    testbase.assert_equal(client.filter_state.datacenter, "dc-1")
    testbase.assert_equal(client.filter_state.folder, "folder-1")
    return


def test_clear_filter_state() -> None:
    client = _make_client()
    client.set_filter_state(datacenter="dc-1")
    client.clear_filter_state()
    testbase.assert_true(client.filter_state.is_empty())
    return


# ----------------------------------------------------------------------
# TestVSphereClientAuthentication
# ----------------------------------------------------------------------


def test_authenticate_mints_token_and_sets_header() -> None:
    client = VSphereClient(host="vc.example.com", credential=_make_credential())

    fake_session = MagicMock()
    fake_session.headers = {}
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"value": "session-token-xyz"}
    fake_session.post.return_value = fake_response

    with patch("ccai.restclient.vsphere.vsphereclient.Session", return_value=fake_session):
        client.authenticate()

    testbase.assert_equal(client.auth_token, "session-token-xyz")
    testbase.assert_equal(fake_session.headers[AUTH_HEADER], "session-token-xyz")
    return


def test_authenticate_non200_raises_httpforbidden() -> None:
    from ccai.errors.exceptions import HttpForbiddenError

    client = VSphereClient(host="vc.example.com", credential=_make_credential())

    fake_session = MagicMock()
    fake_session.headers = {}
    fake_response = MagicMock()
    fake_response.status_code = 401
    fake_response.content = b"nope"
    fake_session.post.return_value = fake_response

    with patch("ccai.restclient.vsphere.vsphereclient.Session", return_value=fake_session):
        with testbase.raises(HttpForbiddenError):
            client.authenticate()
    return


# ----------------------------------------------------------------------
# TestVSphereClientLeafValidation
# ----------------------------------------------------------------------


def test_basegroup_subclass_validates_baseleaf() -> None:
    from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup

    with testbase.raises(SemanticError):

        class BadGroup(BaseGroup):
            BASE_LEAF = "/no-good"

    return
