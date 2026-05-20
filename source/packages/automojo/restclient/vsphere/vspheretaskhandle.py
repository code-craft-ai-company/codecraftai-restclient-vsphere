"""
    .. module:: vspheretaskhandle
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Provides :class:`VSphereTaskHandle`, the sync-poll
        Aspects-driven task handle returned by every long-running
        vSphere call.  Conforms to :class:`ITaskHandle` from
        ``automojo-interfaces``.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Any, Callable, Optional, TYPE_CHECKING

import os
import time
import logging

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from automojo.errors.exceptions import SemanticError
from automojo.interfaces.itaskhandle import (
    ITaskHandle,
    TaskResult,
    TaskState as IfaceTaskState,
)


if TYPE_CHECKING:
    from automojo.restclient.vsphere.aspectsvsphere import AspectsVSphere
    from automojo.restclient.vsphere.vsphereclient import VSphereClient


class TaskState(str, Enum):
    """
        vSphere task lifecycle states.

        ``QUEUED``, ``RUNNING`` are non-terminal.  ``SUCCEEDED``,
        ``FAILED``, ``ERROR``, and ``CANCELLED`` are terminal.
    """
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = frozenset({
    TaskState.SUCCEEDED,
    TaskState.FAILED,
    TaskState.ERROR,
    TaskState.CANCELLED,
})


_IFACE_STATE_MAP = {
    TaskState.QUEUED: IfaceTaskState.PENDING,
    TaskState.RUNNING: IfaceTaskState.RUNNING,
    TaskState.SUCCEEDED: IfaceTaskState.SUCCEEDED,
    TaskState.FAILED: IfaceTaskState.FAILED,
    TaskState.ERROR: IfaceTaskState.FAILED,
    TaskState.CANCELLED: IfaceTaskState.CANCELLED,
}


@dataclass
class TaskInfo:
    """
        Snapshot of a vSphere task's state at one observation point.
    """
    task_id: str
    state: TaskState
    progress_percent: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    description: Optional[str] = None
    target_kind: Optional[str] = None
    target_id: Optional[str] = None
    error: Optional[dict] = field(default=None)


class VSphereTaskFailedError(Exception):
    """
        Raised when a task reaches ``FAILED`` or ``ERROR``.
    """

    def __init__(self, message: str, info: TaskInfo) -> None:
        """
            Initialise with a message and the failing TaskInfo.

            :param message: Multi-line error text.
            :param info: TaskInfo at the time of failure.

            :returns: ``None``
        """
        super().__init__(message)
        self.info = info
        return


class VSphereTaskTimeoutError(TimeoutError):
    """
        Raised when ``wait`` exceeds its aspect timeout.
    """

    def __init__(self, message: str, info: Optional[TaskInfo]) -> None:
        """
            Initialise with a message and the last-observed TaskInfo.

            :param message: Multi-line timeout text.
            :param info: TaskInfo at the time of the timeout, possibly
                ``None`` when no observation was made.

            :returns: ``None``
        """
        super().__init__(message)
        self.info = info
        return


class VSphereTaskNotCancellableError(Exception):
    """
        Raised when ``cancel`` is invoked on a non-cancellable task.
    """


def _parse_task_info(*, task_id: str, payload: dict) -> TaskInfo:
    """
        Parses a vCenter task status payload into a :class:`TaskInfo`.

        :param task_id: The task identifier (forwarded into TaskInfo).
        :param payload: The status payload as a dict.

        :returns: Parsed :class:`TaskInfo`.
    """
    raw_state = payload.get("status")
    if raw_state is None:
        raw_state = payload.get("state")
    if raw_state is None:
        raw_state = "RUNNING"

    try:
        state = TaskState(raw_state)
    except ValueError:
        state = TaskState.RUNNING

    progress_field = payload.get("progress")
    progress_percent = 0
    if isinstance(progress_field, dict):
        completed = progress_field.get("completed", 0)
        if isinstance(completed, int):
            progress_percent = completed
    elif isinstance(progress_field, int):
        progress_percent = progress_field

    target = payload.get("target")
    target_kind = None
    target_id = None
    if isinstance(target, dict):
        target_kind = target.get("type")
        target_id = target.get("id")

    rtnval = TaskInfo(
        task_id=task_id,
        state=state,
        progress_percent=progress_percent,
        started_at=None,
        completed_at=None,
        description=payload.get("description"),
        target_kind=target_kind,
        target_id=target_id,
        error=payload.get("error"),
    )
    return rtnval


class VSphereTaskHandle:
    """
        Synchronous, Aspects-driven handle on a vSphere async task.

        The handle conforms (structurally) to
        :class:`automojo.interfaces.itaskhandle.ITaskHandle` and so is
        recognised by ``isinstance(handle, ITaskHandle)``.

        The poll loop is implemented locally (rather than delegating to
        the generic ``TaskHandle.wait`` in ``automojo-restclient-base``)
        so that it can return the richer :class:`TaskInfo` payload that
        callers expect, raise :class:`VSphereTaskFailedError` on
        ``FAILED``/``ERROR`` terminals, and enforce the
        strict-timeout-gate-at-top-of-iteration invariant declared in
        the spec's poll-loop algorithm.
    """

    TASK_LEAF = "/api/cis/tasks"

    def __init__(
        self,
        *,
        task_id: str,
        client: "VSphereClient",
        status_fetcher: Optional[Callable[[str], dict]] = None,
        canceller: Optional[Callable[[str], None]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        """
            Initialise a task handle.

            :param task_id: vCenter-assigned task identifier.
            :param client: Owning :class:`VSphereClient`; supplies HTTP.
            :param status_fetcher: Optional override for the function
                that retrieves the raw status dict for a given task id.
                Used by tests to drive scripted state sequences without
                a network round-trip.
            :param canceller: Optional override for the cancellation
                callable; ``None`` (default) means cancellation routes
                through the client's normal session.  Pass an explicit
                callable for non-cancellable tasks (raise from inside)
                or for tests that want to assert on the call.
            :param sleeper: Optional override for ``time.sleep``;
                injected by tests to keep the poll loop deterministic.
            :param clock: Optional override for ``time.monotonic``;
                injected by tests.

            :returns: ``None``
        """
        self._task_id = task_id
        self._client = client
        self._status_fetcher = status_fetcher
        self._canceller = canceller
        self._sleeper = sleeper
        self._clock = clock
        self._last_observed_state: Optional[TaskState] = None
        self._last_info: Optional[TaskInfo] = None
        self._transition_log_count: int = 0
        return

    @property
    def transition_log_count(self) -> int:
        """
            Number of state-transition log lines emitted by ``wait``.

            :returns: The integer transition-log counter.
        """
        rtnval = self._transition_log_count
        return rtnval

    def task_id(self) -> str:
        """
            Returns the vCenter task identifier.

            :returns: The task identifier captured at construction.
        """
        rtnval = self._task_id
        return rtnval

    def is_done(self) -> bool:
        """
            Indicates if the most recently observed state is terminal.

            :returns: ``True`` when the last observation was terminal.
        """
        rtnval = False
        if self._last_observed_state is not None:
            if self._last_observed_state in TERMINAL_STATES:
                rtnval = True
        return rtnval

    def status(self, *, aspects: "AspectsVSphere") -> TaskInfo:
        """
            Fetch and parse the current task status as a fresh GET.

            :param aspects: Behaviour controls for the GET.

            :returns: A freshly observed :class:`TaskInfo`.
        """
        payload = self._fetch_status(aspects=aspects)
        info = _parse_task_info(task_id=self._task_id, payload=payload)
        self._last_observed_state = info.state
        self._last_info = info
        return info

    def wait(self, *, aspects: "AspectsVSphere") -> TaskResult:
        """
            Poll until terminal state, raise on failure or timeout.

            Strict-timeout-gate-at-top-of-iteration: the elapsed-time
            check runs before each status GET, so a long-running GET
            cannot blow past the aspect timeout.

            :param aspects: Behaviour controls.  ``completion_interval``
                is the poll interval; ``completion_timeout`` is the
                wall-clock cap.

            :returns: A :class:`TaskResult` describing the terminal
                state.

            :raises: VSphereTaskFailedError, VSphereTaskTimeoutError,
                SemanticError
        """
        interval = aspects.completion_interval
        timeout = aspects.completion_timeout

        if interval <= 0:
            err_msg_lines = [
                "VSphereTaskHandle.wait requires aspects.completion_interval > 0.",
                "GOT interval={}".format(interval),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

        if timeout <= 0:
            err_msg_lines = [
                "VSphereTaskHandle.wait requires aspects.completion_timeout > 0.",
                "GOT timeout={}".format(timeout),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise SemanticError(err_msg)

        clock = self._clock
        if clock is None:
            clock = time.monotonic

        sleeper = self._sleeper
        if sleeper is None:
            sleeper = time.sleep

        logger = aspects.logger
        if logger is None:
            logger = logging.getLogger("automojo.restclient.vsphere")

        started = clock()
        last_state: Optional[TaskState] = None
        last_info: Optional[TaskInfo] = None

        rtnval: Optional[TaskResult] = None

        while True:

            elapsed = clock() - started
            if elapsed > timeout:
                err_msg_lines = [
                    "VSphereTaskHandle.wait timed out.",
                    "TASK: {}".format(self._task_id),
                    "TIMEOUT: {}s".format(timeout),
                    "ELAPSED: {}s".format(elapsed),
                    "LAST STATE: {}".format(
                        last_state.value if last_state is not None else "<none>"
                    ),
                ]
                err_msg = os.linesep.join(err_msg_lines)
                raise VSphereTaskTimeoutError(err_msg, info=last_info)

            info = self.status(aspects=aspects)
            last_info = info

            if info.state != last_state:
                logger.info(
                    "task %s state: %s",
                    self._task_id,
                    info.state.value,
                )
                self._transition_log_count = self._transition_log_count + 1
                last_state = info.state

            if info.state in TERMINAL_STATES:
                if info.state == TaskState.SUCCEEDED:
                    rtnval = TaskResult(
                        task_id=self._task_id,
                        state=_IFACE_STATE_MAP[info.state],
                        progress=info.progress_percent,
                        error=None,
                        payload=None,
                    )
                    break

                if info.state == TaskState.CANCELLED:
                    rtnval = TaskResult(
                        task_id=self._task_id,
                        state=_IFACE_STATE_MAP[info.state],
                        progress=info.progress_percent,
                        error=None,
                        payload=None,
                    )
                    break

                err_msg_lines = [
                    "VSphere task reached non-success terminal state.",
                    "TASK: {}".format(self._task_id),
                    "STATE: {}".format(info.state.value),
                ]
                if info.error is not None:
                    err_msg_lines.append("ERROR: {!r}".format(info.error))
                err_msg = os.linesep.join(err_msg_lines)
                raise VSphereTaskFailedError(err_msg, info=info)

            sleeper(interval)

        return rtnval

    def cancel(self, *, aspects: "AspectsVSphere") -> None:
        """
            Cancel the in-flight task.

            When the task is already in a terminal state, this method
            is a no-op.  When the task type does not support
            cancellation, raises :class:`VSphereTaskNotCancellableError`.

            :param aspects: Behaviour controls.

            :returns: ``None``

            :raises: VSphereTaskNotCancellableError
        """
        if self._last_observed_state is not None:
            if self._last_observed_state in TERMINAL_STATES:
                return None

        canceller = self._canceller
        if canceller is None:
            client = self._client
            cancel_leaf = "{}/{}?action=cancel".format(self.TASK_LEAF, self._task_id)
            cancel_url = client.build_url(leaf=cancel_leaf)
            session = client.ensure_session(aspects=aspects)
            resp = session.post(cancel_url, timeout=aspects.completion_timeout)
            status_code = resp.status_code
            if status_code == 400 or status_code == 405:
                err_msg_lines = [
                    "Task is not cancellable.",
                    "TASK: {}".format(self._task_id),
                    "STATUS: {}".format(status_code),
                ]
                err_msg = os.linesep.join(err_msg_lines)
                raise VSphereTaskNotCancellableError(err_msg)
        else:
            canceller(self._task_id)

        return None

    def _fetch_status(self, *, aspects: "AspectsVSphere") -> dict:
        """
            Fetch the raw status dict for the task id.

            :param aspects: Behaviour controls for the GET.

            :returns: The raw payload as a dictionary.
        """
        fetcher = self._status_fetcher
        if fetcher is not None:
            rtnval = fetcher(self._task_id)
            return rtnval

        client = self._client
        status_leaf = "{}/{}".format(self.TASK_LEAF, self._task_id)
        status_url = client.build_url(leaf=status_leaf)
        session = client.ensure_session(aspects=aspects)
        resp = session.get(status_url, timeout=aspects.completion_timeout)
        rtnval = resp.json()
        return rtnval


# Runtime conformance attestation.  ``ITaskHandle`` is a
# ``@runtime_checkable`` Protocol, so isinstance() works structurally;
# this assignment exists purely to make the structural relationship
# obvious to readers and to lock the import into the module.
_ITASKHANDLE_PROTOCOL = ITaskHandle
