"""
    Tests for :class:`VSphereClient`: construction, URL composition,
    property-based group access, filter state, authentication, and
    session renewal.
"""

import unittest

from unittest.mock import MagicMock, patch

from ccai.credentials.basiccredential import BasicCredential
from ccai.credentials.publickeycredential import PublicKeyCredential
from ccai.errors.exceptions import SemanticError

from ccai.restclient.vsphere.vsphereclient import VSphereClient
from ccai.restclient.vsphere.aspectsvsphere import DEFAULT_VSPHERE_ASPECTS
from ccai.restclient.vsphere.vspheresession import AUTH_HEADER


def _make_credential() -> BasicCredential:
    rtnval = BasicCredential(
        identifier="vc-login",
        categories=["basic"],
        username="administrator@vsphere.local",
        password="hunter2",
    )
    return rtnval


class TestVSphereClientConstruction(unittest.TestCase):

    def test_construct_with_basic_credential(self) -> None:
        client = VSphereClient(host="vc.example.com", credential=_make_credential())
        self.assertEqual(client.host, "vc.example.com")
        self.assertIsNone(client.auth_token)
        return

    def test_construct_with_wrong_credential_type_raises_semantic(self) -> None:
        bad = MagicMock(spec=object)
        with self.assertRaises(SemanticError):
            VSphereClient(host="vc.example.com", credential=bad)
        return

    def test_no_io_on_construct(self) -> None:
        # Patch Session at the module level used by the session-mint
        # helper.  If construction issues network I/O, this would be
        # called.
        with patch("ccai.restclient.vsphere.vsphereclient.Session") as session_cls:
            client = VSphereClient(host="vc.example.com", credential=_make_credential())
            self.assertEqual(session_cls.call_count, 0)
            _ = client
        return


class TestVSphereClientUrlComposition(unittest.TestCase):

    def setUp(self) -> None:
        self.client = VSphereClient(host="vc.example.com", credential=_make_credential())
        return

    def test_build_url_accepts_api_prefix(self) -> None:
        url = self.client.build_url(leaf="/api/vcenter/vm")
        self.assertEqual(url, "https://vc.example.com/api/vcenter/vm")
        return

    def test_build_url_accepts_rest_prefix(self) -> None:
        url = self.client.build_url(leaf="/rest/com/vmware/cis/session")
        self.assertEqual(url, "https://vc.example.com/rest/com/vmware/cis/session")
        return

    def test_build_url_rejects_unknown_prefix(self) -> None:
        with self.assertRaises(SemanticError):
            self.client.build_url(leaf="/legacy/no/prefix")
        return

    def test_build_api_url_normalizes(self) -> None:
        url = self.client.build_api_url(leaf="/vcenter/datacenter")
        self.assertEqual(url, "https://vc.example.com/api/vcenter/datacenter")
        return

    def test_build_rest_url_normalizes(self) -> None:
        url = self.client.build_rest_url(leaf="/com/vmware/cis/session")
        self.assertEqual(url, "https://vc.example.com/rest/com/vmware/cis/session")
        return


class TestVSphereClientGroupAccess(unittest.TestCase):

    def setUp(self) -> None:
        self.client = VSphereClient(host="vc.example.com", credential=_make_credential())
        return

    def test_vm_group_property_returns_vmgroup(self) -> None:
        from ccai.restclient.vsphere.apigroups.vmgroup import VmGroup
        vm = self.client.Vm
        self.assertIsInstance(vm, VmGroup)
        return

    def test_group_property_is_cached_identity(self) -> None:
        first = self.client.Vm
        second = self.client.Vm
        self.assertIs(first, second)
        return

    def test_legacy_alias_resolves_to_canonical(self) -> None:
        canonical = self.client.Datacenter
        legacy = self.client.DataCenter
        self.assertIs(canonical, legacy)
        return

    def test_unknown_group_raises_attributeerror(self) -> None:
        with self.assertRaises(AttributeError) as ctx:
            _ = self.client.NoSuchGroup
        # Helpful message must list available groups.
        message = str(ctx.exception)
        self.assertIn("AVAILABLE GROUPS", message)
        self.assertIn("Vm", message)
        return


class TestVSphereClientFilterState(unittest.TestCase):

    def setUp(self) -> None:
        self.client = VSphereClient(host="vc.example.com", credential=_make_credential())
        return

    def test_initial_filter_state_is_empty(self) -> None:
        self.assertTrue(self.client.filter_state.is_empty())
        return

    def test_set_filter_state(self) -> None:
        self.client.set_filter_state(datacenter="dc-1", folder="folder-1")
        self.assertEqual(self.client.filter_state.datacenter, "dc-1")
        self.assertEqual(self.client.filter_state.folder, "folder-1")
        return

    def test_clear_filter_state(self) -> None:
        self.client.set_filter_state(datacenter="dc-1")
        self.client.clear_filter_state()
        self.assertTrue(self.client.filter_state.is_empty())
        return


class TestVSphereClientAuthentication(unittest.TestCase):

    def test_authenticate_mints_token_and_sets_header(self) -> None:
        client = VSphereClient(host="vc.example.com", credential=_make_credential())

        fake_session = MagicMock()
        fake_session.headers = {}
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"value": "session-token-xyz"}
        fake_session.post.return_value = fake_response

        with patch("ccai.restclient.vsphere.vsphereclient.Session", return_value=fake_session):
            client.authenticate()

        self.assertEqual(client.auth_token, "session-token-xyz")
        self.assertEqual(fake_session.headers[AUTH_HEADER], "session-token-xyz")
        return

    def test_authenticate_non200_raises_httpforbidden(self) -> None:
        from ccai.errors.exceptions import HttpForbiddenError

        client = VSphereClient(host="vc.example.com", credential=_make_credential())

        fake_session = MagicMock()
        fake_session.headers = {}
        fake_response = MagicMock()
        fake_response.status_code = 401
        fake_response.content = b"nope"
        fake_session.post.return_value = fake_response

        with patch("ccai.restclient.vsphere.vsphereclient.Session", return_value=fake_session):
            with self.assertRaises(HttpForbiddenError):
                client.authenticate()
        return


class TestVSphereClientLeafValidation(unittest.TestCase):

    def test_basegroup_subclass_validates_baseleaf(self) -> None:
        from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup
        with self.assertRaises(SemanticError):

            class BadGroup(BaseGroup):
                BASE_LEAF = "/no-good"

        return


if __name__ == "__main__":
    unittest.main()
