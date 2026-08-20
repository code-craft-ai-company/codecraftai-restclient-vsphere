"""
    Tests for vSphere VM lifecycle waiters:
    - VmGroup.wait_for_power_state
    - GuestGroup.wait_for_tools_ready
    - GuestGroup.wait_for_ip_address

    Time and HTTP are mocked; the waiters accept injected
    state_fetcher/clock/sleeper callables for deterministic tests.
"""


from typing import List
from unittest.mock import MagicMock

from ccai import testbase

from ccai.credentials.basiccredential import BasicCredential

from ccai.restclient.vsphere.apigroups.waiters import (
    VSphereWaitInvalidStateError,
    VSphereWaitTimeoutError,
)
from ccai.restclient.vsphere.aspectsvsphere import AspectsVSphere
from ccai.restclient.vsphere.enums.powerstate import PowerState
from ccai.restclient.vsphere.vsphereclient import VSphereClient


def _make_client() -> VSphereClient:
    cred = BasicCredential(
        identifier="vc", categories=["basic"], username="u", password="p",
    )
    rtnval = VSphereClient(host="vc.example.com", credential=cred)
    rtnval._session = MagicMock()
    rtnval._auth_token = "token-1"
    return rtnval


def _aspects(*, timeout: float = 5.0, interval: float = 0.01) -> AspectsVSphere:
    rtnval = AspectsVSphere(
        completion_timeout=timeout, completion_interval=interval,
    )
    return rtnval


class _Clock:
    """Deterministic fake clock that advances by ``step`` each call."""

    def __init__(self, *, step: float = 0.5) -> None:
        self._t = 0.0
        self._step = step
        return

    def __call__(self) -> float:
        rtnval = self._t
        self._t = self._t + self._step
        return rtnval


def _scripted_state_fetcher(*, values: List):
    """Return a fetcher that yields ``values`` then keeps the last."""
    seq = list(values)

    def _fetch(_vmid: str):
        if len(seq) > 1:
            rtnval = seq.pop(0)
            return rtnval
        rtnval = seq[0]
        return rtnval

    return _fetch


# ----------------------------------------------------------------------
# TestWaitForPowerStateHappy
# ----------------------------------------------------------------------


def test_target_reached_first_poll() -> None:
    client = _make_client()
    aspects = _aspects()
    fetcher = _scripted_state_fetcher(values=[PowerState.POWERED_ON])
    sleeper = MagicMock()
    result = client.Vm.wait_for_power_state(
        vm="vm-1",
        desired=PowerState.POWERED_ON,
        aspects=aspects,
        state_fetcher=fetcher,
        sleeper=sleeper,
        clock=_Clock(step=0.0),
    )
    testbase.assert_equal(result, PowerState.POWERED_ON)
    sleeper.assert_not_called()
    return

def test_target_reached_after_transitions() -> None:
    client = _make_client()
    aspects = _aspects()
    fetcher = _scripted_state_fetcher(values=[
        PowerState.POWERED_OFF,
        PowerState.POWERED_OFF,
        PowerState.POWERED_ON,
    ])
    sleeper = MagicMock()
    result = client.Vm.wait_for_power_state(
        vm="vm-1",
        desired=PowerState.POWERED_ON,
        aspects=aspects,
        state_fetcher=fetcher,
        sleeper=sleeper,
        clock=_Clock(step=0.1),
    )
    testbase.assert_equal(result, PowerState.POWERED_ON)
    testbase.assert_true(sleeper.call_count >= 2)
    return


# ----------------------------------------------------------------------
# TestWaitForPowerStateTimeout
# ----------------------------------------------------------------------


def test_timeout_raises() -> None:
    client = _make_client()
    aspects = _aspects(timeout=1.0, interval=0.01)
    # State never advances to POWERED_ON.
    fetcher = _scripted_state_fetcher(values=[PowerState.POWERED_OFF])
    # Clock jumps past the timeout on the second call.
    clock_seq = iter([0.0, 0.5, 2.0])

    def _clock() -> float:
        rtnval = next(clock_seq)
        return rtnval

    with testbase.raises(VSphereWaitTimeoutError) as cm:
        client.Vm.wait_for_power_state(
            vm="vm-1",
            desired=PowerState.POWERED_ON,
            aspects=aspects,
            state_fetcher=fetcher,
            sleeper=MagicMock(),
            clock=_clock,
        )
    testbase.assert_equal(cm.exception.observed, PowerState.POWERED_OFF)
    return


# ----------------------------------------------------------------------
# TestWaitForToolsReady
# ----------------------------------------------------------------------


def test_immediate() -> None:
    client = _make_client()
    aspects = _aspects()
    fetcher = _scripted_state_fetcher(values=["RUNNING"])
    sleeper = MagicMock()
    result = client.Guest.wait_for_tools_ready(
        vm="vm-1",
        aspects=aspects,
        state_fetcher=fetcher,
        sleeper=sleeper,
        clock=_Clock(step=0.0),
    )
    testbase.assert_equal(result, "RUNNING")
    sleeper.assert_not_called()
    return

def test_eventually_running() -> None:
    client = _make_client()
    aspects = _aspects()
    fetcher = _scripted_state_fetcher(values=[
        "NOT_RUNNING", "STARTING", "RUNNING",
    ])
    sleeper = MagicMock()
    result = client.Guest.wait_for_tools_ready(
        vm="vm-1",
        aspects=aspects,
        state_fetcher=fetcher,
        sleeper=sleeper,
        clock=_Clock(step=0.1),
    )
    testbase.assert_equal(result, "RUNNING")
    return

def test_wait_for_tools_ready_timeout() -> None:
    client = _make_client()
    aspects = _aspects(timeout=1.0)
    fetcher = _scripted_state_fetcher(values=["NOT_RUNNING"])
    clock_seq = iter([0.0, 0.5, 2.0])

    def _clock() -> float:
        rtnval = next(clock_seq)
        return rtnval

    with testbase.raises(VSphereWaitTimeoutError) as cm:
        client.Guest.wait_for_tools_ready(
            vm="vm-1",
            aspects=aspects,
            state_fetcher=fetcher,
            sleeper=MagicMock(),
            clock=_clock,
        )
    testbase.assert_equal(cm.exception.observed, "NOT_RUNNING")
    return


# ----------------------------------------------------------------------
# TestWaitForIpAddress
# ----------------------------------------------------------------------


def _nics(*, addr: str, family: str = "IPV4"):
    rtnval = [{
        "ip": {
            "ip_addresses": [
                {"ip_address_family": family, "ip_address": addr},
            ],
        },
    }]
    return rtnval

def test_ipv4_happy() -> None:
    client = _make_client()
    aspects = _aspects()
    nics_seq = [[], _nics(addr="10.0.0.5", family="IPV4")]

    def _fetch_nics(_vmid):
        rtnval = nics_seq.pop(0) if len(nics_seq) > 1 else nics_seq[0]
        return rtnval

    result = client.Guest.wait_for_ip_address(
        vm="vm-1",
        nic_index=0,
        family="ipv4",
        aspects=aspects,
        networking_fetcher=_fetch_nics,
        sleeper=MagicMock(),
        clock=_Clock(step=0.1),
    )
    testbase.assert_equal(result, "10.0.0.5")
    return

def test_ipv6_happy() -> None:
    client = _make_client()
    aspects = _aspects()
    nics = _nics(addr="fe80::1", family="IPV6")

    def _fetch_nics(_vmid):
        return nics

    result = client.Guest.wait_for_ip_address(
        vm="vm-1",
        family="ipv6",
        aspects=aspects,
        networking_fetcher=_fetch_nics,
        sleeper=MagicMock(),
        clock=_Clock(step=0.0),
    )
    testbase.assert_equal(result, "fe80::1")
    return

def test_wait_for_ip_address_timeout() -> None:
    client = _make_client()
    aspects = _aspects(timeout=1.0)
    clock_seq = iter([0.0, 0.5, 2.0])

    def _clock() -> float:
        rtnval = next(clock_seq)
        return rtnval

    def _fetch_nics(_vmid):
        return []

    with testbase.raises(VSphereWaitTimeoutError):
        client.Guest.wait_for_ip_address(
            vm="vm-1",
            aspects=aspects,
            networking_fetcher=_fetch_nics,
            sleeper=MagicMock(),
            clock=_clock,
        )
    return

def test_mid_wait_power_off_raises() -> None:
    client = _make_client()
    aspects = _aspects()

    def _fetch_nics(_vmid):
        return []

    def _fetch_power(_vmid):
        return PowerState.POWERED_OFF

    with testbase.raises(VSphereWaitInvalidStateError) as cm:
        client.Guest.wait_for_ip_address(
            vm="vm-1",
            aspects=aspects,
            networking_fetcher=_fetch_nics,
            power_state_fetcher=_fetch_power,
            sleeper=MagicMock(),
            clock=_Clock(step=0.0),
        )
    testbase.assert_equal(cm.exception.observed, PowerState.POWERED_OFF)
    return

def test_invalid_family_raises_semantic() -> None:
    from ccai.errors.exceptions import SemanticError
    client = _make_client()
    aspects = _aspects()
    with testbase.raises(SemanticError):
        client.Guest.wait_for_ip_address(
            vm="vm-1",
            family="ipv7",
            aspects=aspects,
            networking_fetcher=lambda _v: [],
            sleeper=MagicMock(),
            clock=_Clock(step=0.0),
        )
    return
