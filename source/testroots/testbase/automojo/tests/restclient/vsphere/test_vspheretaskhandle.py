"""
    Tests for :class:`VSphereTaskHandle`: status polling, wait happy
    path, wait failure path, wait timeout, cancellation,
    ``ITaskHandle`` conformance, and the property-based poll-loop
    convergence test.
"""

import unittest

from typing import Dict, List, Optional

from unittest.mock import MagicMock

from hypothesis import given, settings, strategies as st

from automojo.errors.exceptions import SemanticError
from automojo.interfaces.itaskhandle import ITaskHandle
from automojo.restclient.vsphere.aspectsvsphere import AspectsVSphere
from automojo.restclient.vsphere.vspheretaskhandle import (
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


class TestVSphereTaskHandleConstruction(unittest.TestCase):

    def test_construct_no_io(self) -> None:
        client = MagicMock()
        handle = VSphereTaskHandle(task_id="t-1", client=client)
        self.assertEqual(handle.task_id(), "t-1")
        self.assertFalse(handle.is_done())
        client.assert_not_called()
        return


class TestVSphereTaskHandleStatus(unittest.TestCase):

    def test_status_invokes_fetcher_each_call(self) -> None:
        client = MagicMock()
        fetcher = MagicMock(return_value={"status": "RUNNING"})
        handle = VSphereTaskHandle(task_id="t-1", client=client, status_fetcher=fetcher)
        handle.status(aspects=_aspects())
        handle.status(aspects=_aspects())
        self.assertEqual(fetcher.call_count, 2)
        return

    def test_status_parses_state(self) -> None:
        client = MagicMock()
        fetcher = _scripted_fetcher([TaskState.RUNNING])
        handle = VSphereTaskHandle(task_id="t-1", client=client, status_fetcher=fetcher)
        info = handle.status(aspects=_aspects())
        self.assertEqual(info.state, TaskState.RUNNING)
        return


class TestVSphereTaskHandleWait(unittest.TestCase):

    def test_wait_succeeds(self) -> None:
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
        self.assertTrue(handle.is_done())
        self.assertEqual(result.task_id, "t-1")
        return

    def test_wait_failure_raises(self) -> None:
        client = MagicMock()
        fetcher = _scripted_fetcher([TaskState.RUNNING, TaskState.FAILED])
        handle = VSphereTaskHandle(
            task_id="t-2",
            client=client,
            status_fetcher=fetcher,
            sleeper=lambda s: None,
        )
        with self.assertRaises(VSphereTaskFailedError) as ctx:
            handle.wait(aspects=_aspects())
        self.assertEqual(ctx.exception.info.state, TaskState.FAILED)
        return

    def test_wait_error_raises(self) -> None:
        client = MagicMock()
        fetcher = _scripted_fetcher([TaskState.ERROR])
        handle = VSphereTaskHandle(
            task_id="t-3",
            client=client,
            status_fetcher=fetcher,
            sleeper=lambda s: None,
        )
        with self.assertRaises(VSphereTaskFailedError):
            handle.wait(aspects=_aspects())
        return

    def test_wait_timeout_raises(self) -> None:
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
        with self.assertRaises(VSphereTaskTimeoutError):
            handle.wait(aspects=_aspects(completion_timeout=1.0))
        return

    def test_wait_invalid_aspects_raises(self) -> None:
        client = MagicMock()
        handle = VSphereTaskHandle(task_id="t-5", client=client)
        bad = AspectsVSphere(completion_timeout=1.0, completion_interval=0.0)
        with self.assertRaises(SemanticError):
            handle.wait(aspects=bad)
        return


class TestVSphereTaskHandleCancel(unittest.TestCase):

    def test_cancel_already_terminal_noop(self) -> None:
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

    def test_cancel_calls_canceller(self) -> None:
        client = MagicMock()
        canceller = MagicMock()
        handle = VSphereTaskHandle(
            task_id="t-1", client=client, canceller=canceller,
        )
        handle._last_observed_state = TaskState.RUNNING
        handle.cancel(aspects=_aspects())
        canceller.assert_called_once_with("t-1")
        return

    def test_cancel_not_cancellable_raises(self) -> None:
        client = MagicMock()

        def canceller(task_id: str) -> None:
            raise VSphereTaskNotCancellableError("nope")

        handle = VSphereTaskHandle(
            task_id="t-1", client=client, canceller=canceller,
        )
        handle._last_observed_state = TaskState.RUNNING
        with self.assertRaises(VSphereTaskNotCancellableError):
            handle.cancel(aspects=_aspects())
        return


class TestVSphereTaskHandleProtocolConformance(unittest.TestCase):

    def test_isinstance_itaskhandle(self) -> None:
        client = MagicMock()
        handle = VSphereTaskHandle(task_id="t-1", client=client)
        self.assertIsInstance(handle, ITaskHandle)
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


class TestVSphereTaskHandleProperties(unittest.TestCase):

    @settings(max_examples=50, deadline=None)
    @given(_state_sequence_with_terminal())
    def test_any_sequence_with_terminal_converges(self, sequence) -> None:
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
            self.assertTrue(handle.is_done())
        else:
            with self.assertRaises(VSphereTaskFailedError):
                handle.wait(aspects=_aspects())
        return

    @settings(max_examples=50, deadline=None)
    @given(st.lists(st.sampled_from(_NON_TERMINAL_STATES), min_size=1, max_size=5))
    def test_no_terminal_then_timeout(self, prefix) -> None:
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
        with self.assertRaises(VSphereTaskTimeoutError):
            handle.wait(aspects=_aspects(completion_timeout=1.0))
        return

    @settings(max_examples=20, deadline=None)
    @given(_state_sequence_with_terminal())
    def test_transition_log_count_equals_distinct_transitions(self, sequence) -> None:
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
            with self.assertRaises(VSphereTaskFailedError):
                handle.wait(aspects=_aspects())

        self.assertEqual(handle.transition_log_count, expected)
        return


if __name__ == "__main__":
    unittest.main()
