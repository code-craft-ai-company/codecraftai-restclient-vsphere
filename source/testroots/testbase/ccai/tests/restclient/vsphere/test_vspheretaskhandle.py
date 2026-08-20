"""
    Tests for :class:`VSphereTaskHandle`: status polling, wait happy
    path, wait failure path, wait timeout, cancellation,
    ``ITaskHandle`` conformance, and the property-based poll-loop
    convergence test.
"""


from typing import Dict, List, Optional

from unittest.mock import MagicMock

from ccai import testbase

from ccai.testbase.properties import given
from ccai.testbase.properties import strategies as st

from ccai.errors.exceptions import SemanticError
from ccai.interfaces.itaskhandle import ITaskHandle
from ccai.restclient.vsphere.aspectsvsphere import AspectsVSphere
from ccai.restclient.vsphere.vspheretaskhandle import (
    TaskInfo,
    TaskState,
    TERMINAL_STATES,
    VSphereTaskFailedError,
    VSphereTaskHandle,
    VSphereTaskNotCancellableError,
    VSphereTaskTimeoutError,
)


def _scripted_fetcher(states):
    """
        Build a status-fetcher that yields the given sequence of states.

        :param states: Iterable of :class:`TaskState` values.

        :returns: A callable accepting ``task_id`` and returning a
            payload dict whose ``status`` is the next scripted state.
    """
    seq = list(states)

    def fetch(task_id: str) -> Dict:
        if len(seq) == 0:
            payload = {"status": TaskState.RUNNING.value}
            return payload
        next_state = seq.pop(0)
        payload = {"status": next_state.value, "progress": {"completed": 0}}
        return payload

    return fetch


def _aspects(
    *,
    completion_timeout: float = 1.0,
    completion_interval: float = 0.01,
) -> AspectsVSphere:
    rtnval = AspectsVSphere(
        completion_timeout=completion_timeout,
        completion_interval=completion_interval,
    )
    return rtnval


# ----------------------------------------------------------------------
# TestVSphereTaskHandleConstruction
# ----------------------------------------------------------------------


def test_construct_no_io() -> None:
    client = MagicMock()
    handle = VSphereTaskHandle(task_id="t-1", client=client)
    testbase.assert_equal(handle.task_id(), "t-1")
    testbase.assert_false(handle.is_done())
    client.assert_not_called()
    return


# ----------------------------------------------------------------------
# TestVSphereTaskHandleStatus
# ----------------------------------------------------------------------


def test_status_invokes_fetcher_each_call() -> None:
    client = MagicMock()
    fetcher = MagicMock(return_value={"status": "RUNNING"})
    handle = VSphereTaskHandle(task_id="t-1", client=client, status_fetcher=fetcher)
    handle.status(aspects=_aspects())
    handle.status(aspects=_aspects())
    testbase.assert_equal(fetcher.call_count, 2)
    return

def test_status_parses_state() -> None:
    client = MagicMock()
    fetcher = _scripted_fetcher([TaskState.RUNNING])
    handle = VSphereTaskHandle(task_id="t-1", client=client, status_fetcher=fetcher)
    info = handle.status(aspects=_aspects())
    testbase.assert_equal(info.state, TaskState.RUNNING)
    return


# ----------------------------------------------------------------------
# TestVSphereTaskHandleFetchStatus
# ----------------------------------------------------------------------

"""
    Regression coverage for the ``_fetch_status`` HTTP status check
    (audit MEDIUM: ``_fetch_status`` decoded ``resp.json()`` without
    a status check).
"""

def test_fetch_status_raises_on_non_ok_status() -> None:
    bad_resp = MagicMock()
    bad_resp.status_code = 500
    bad_resp.content = b"internal error"

    session = MagicMock()
    session.get = MagicMock(return_value=bad_resp)

    client = MagicMock()
    client.build_url = MagicMock(return_value="https://vc/api/task/t-1")
    client.ensure_session = MagicMock(return_value=session)

    handle = VSphereTaskHandle(task_id="t-1", client=client)

    with testbase.raises(Exception):
        handle.status(aspects=_aspects())

    # The body must NOT have been decoded on a non-2xx response.
    bad_resp.json.assert_not_called()
    return


# ----------------------------------------------------------------------
# TestVSphereTaskHandleWait
# ----------------------------------------------------------------------


def test_wait_succeeds() -> None:
    client = MagicMock()
    fetcher = _scripted_fetcher([
        TaskState.QUEUED,
        TaskState.RUNNING,
        TaskState.SUCCEEDED,
    ])
    sleeps: List[float] = []
    handle = VSphereTaskHandle(
        task_id="t-1",
        client=client,
        status_fetcher=fetcher,
        sleeper=lambda s: sleeps.append(s),
    )
    result = handle.wait(aspects=_aspects())
    testbase.assert_true(handle.is_done())
    testbase.assert_equal(result.task_id, "t-1")
    return

def test_wait_failure_raises() -> None:
    client = MagicMock()
    fetcher = _scripted_fetcher([TaskState.RUNNING, TaskState.FAILED])
    handle = VSphereTaskHandle(
        task_id="t-2",
        client=client,
        status_fetcher=fetcher,
        sleeper=lambda s: None,
    )
    with testbase.raises(VSphereTaskFailedError) as ctx:
        handle.wait(aspects=_aspects())
    testbase.assert_equal(ctx.exception.info.state, TaskState.FAILED)
    return

def test_wait_error_raises() -> None:
    client = MagicMock()
    fetcher = _scripted_fetcher([TaskState.ERROR])
    handle = VSphereTaskHandle(
        task_id="t-3",
        client=client,
        status_fetcher=fetcher,
        sleeper=lambda s: None,
    )
    with testbase.raises(VSphereTaskFailedError):
        handle.wait(aspects=_aspects())
    return

def test_wait_timeout_raises() -> None:
    client = MagicMock()
    # Always returns RUNNING; mocked clock advances past timeout.
    fetcher = lambda task_id: {"status": "RUNNING"}
    ticks = [0.0, 0.0, 5.0, 10.0]

    def clock() -> float:
        if len(ticks) > 1:
            rtn = ticks.pop(0)
        else:
            rtn = ticks[0]
        return rtn

    handle = VSphereTaskHandle(
        task_id="t-4",
        client=client,
        status_fetcher=fetcher,
        sleeper=lambda s: None,
        clock=clock,
    )
    with testbase.raises(VSphereTaskTimeoutError):
        handle.wait(aspects=_aspects(completion_timeout=1.0))
    return

def test_wait_invalid_aspects_raises() -> None:
    client = MagicMock()
    handle = VSphereTaskHandle(task_id="t-5", client=client)
    bad = AspectsVSphere(completion_timeout=1.0, completion_interval=0.0)
    with testbase.raises(SemanticError):
        handle.wait(aspects=bad)
    return


# ----------------------------------------------------------------------
# TestVSphereTaskHandleCancel
# ----------------------------------------------------------------------


def test_cancel_already_terminal_noop() -> None:
    client = MagicMock()
    canceller = MagicMock()
    handle = VSphereTaskHandle(
        task_id="t-1", client=client, canceller=canceller,
    )
    # Drive a terminal observation.
    handle._last_observed_state = TaskState.SUCCEEDED
    handle.cancel(aspects=_aspects())
    canceller.assert_not_called()
    return

def test_cancel_calls_canceller() -> None:
    client = MagicMock()
    canceller = MagicMock()
    handle = VSphereTaskHandle(
        task_id="t-1", client=client, canceller=canceller,
    )
    handle._last_observed_state = TaskState.RUNNING
    handle.cancel(aspects=_aspects())
    canceller.assert_called_once_with("t-1")
    return

def test_cancel_not_cancellable_raises() -> None:
    client = MagicMock()

    def canceller(task_id: str) -> None:
        raise VSphereTaskNotCancellableError("nope")

    handle = VSphereTaskHandle(
        task_id="t-1", client=client, canceller=canceller,
    )
    handle._last_observed_state = TaskState.RUNNING
    with testbase.raises(VSphereTaskNotCancellableError):
        handle.cancel(aspects=_aspects())
    return


# ----------------------------------------------------------------------
# TestVSphereTaskHandleProtocolConformance
# ----------------------------------------------------------------------


def test_isinstance_itaskhandle() -> None:
    client = MagicMock()
    handle = VSphereTaskHandle(task_id="t-1", client=client)
    testbase.assert_true(isinstance(handle, ITaskHandle))
    return


# ---------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------

_NON_TERMINAL_STATES = (TaskState.QUEUED, TaskState.RUNNING)
_RAISING_TERMINALS = (TaskState.FAILED, TaskState.ERROR)


@st.composite
def _state_sequence_with_terminal(draw):
    """
        Generate a finite state sequence that ends with a terminal
        state.
    """
    prefix = draw(st.lists(st.sampled_from(_NON_TERMINAL_STATES), max_size=10))
    terminal = draw(st.sampled_from([
        TaskState.SUCCEEDED,
        TaskState.FAILED,
        TaskState.ERROR,
    ]))
    return prefix + [terminal]


# ----------------------------------------------------------------------
# TestVSphereTaskHandleProperties
# ----------------------------------------------------------------------


@given(_state_sequence_with_terminal(), constraints={"max_examples": 50})
def test_any_sequence_with_terminal_converges(sequence) -> None:
    client = MagicMock()
    handle = VSphereTaskHandle(
        task_id="t-prop",
        client=client,
        status_fetcher=_scripted_fetcher(sequence),
        sleeper=lambda s: None,
    )
    terminal = sequence[-1]
    if terminal == TaskState.SUCCEEDED:
        result = handle.wait(aspects=_aspects())
        testbase.assert_true(handle.is_done())
    else:
        with testbase.raises(VSphereTaskFailedError):
            handle.wait(aspects=_aspects())
    return

@given(st.lists(st.sampled_from(_NON_TERMINAL_STATES), min_size=1, max_size=5), constraints={"max_examples": 50})
def test_no_terminal_then_timeout(prefix) -> None:
    client = MagicMock()
    # Fetcher returns RUNNING forever; clock fires past timeout
    # after the first observation.
    fetcher = lambda task_id: {"status": "RUNNING"}

    # Drive monotonic past the timeout immediately.
    sequence = [0.0, 0.0, 100.0]

    def clock() -> float:
        if len(sequence) > 1:
            rtn = sequence.pop(0)
        else:
            rtn = sequence[0]
        return rtn

    _ = prefix
    handle = VSphereTaskHandle(
        task_id="t-prop-2",
        client=client,
        status_fetcher=fetcher,
        sleeper=lambda s: None,
        clock=clock,
    )
    with testbase.raises(VSphereTaskTimeoutError):
        handle.wait(aspects=_aspects(completion_timeout=1.0))
    return

@given(_state_sequence_with_terminal(), constraints={"max_examples": 20})
def test_transition_log_count_equals_distinct_transitions(sequence) -> None:
    client = MagicMock()
    sleeps: List[float] = []
    handle = VSphereTaskHandle(
        task_id="t-prop-3",
        client=client,
        status_fetcher=_scripted_fetcher(sequence),
        sleeper=lambda s: sleeps.append(s),
    )

    # Count expected transitions: 1 for the initial observation,
    # plus one for every adjacent-state change.
    expected = 1
    prev = sequence[0]
    for state in sequence[1:]:
        if state != prev:
            expected = expected + 1
            prev = state

    if sequence[-1] == TaskState.SUCCEEDED:
        handle.wait(aspects=_aspects())
    else:
        with testbase.raises(VSphereTaskFailedError):
            handle.wait(aspects=_aspects())

    testbase.assert_equal(handle.transition_log_count, expected)
    return
