"""
    .. module:: waiters
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Shared exception classes for vSphere VM lifecycle
        waiters.  Lives next to the api-group modules so the waiter
        methods (declared on ``VmGroup`` / ``GuestGroup``) can import
        them without a circular dependency.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Any


class VSphereWaitTimeoutError(Exception):
    """
        Raised when a vSphere lifecycle waiter exceeds the timeout
        configured on :class:`AspectsVSphere`.

        The last observation made before the timeout is attached as
        ``observed`` so callers can produce structured diagnostics.
    """

    def __init__(self, message: str, observed: Any = None) -> None:
        """
            Initialise the error with a message and the last observation.

            :param message: Multi-line error text.
            :param observed: The last observation made before the
                timeout (e.g. a :class:`PowerState` value, a tools-state
                string, or a dict of NIC records).

            :returns: ``None``
        """
        super().__init__(message)
        self.observed = observed
        return


class VSphereWaitInvalidStateError(Exception):
    """
        Raised when a waiter observes an obviously invalid mid-wait
        state — for example a VM transitioning to ``POWERED_OFF``
        during ``wait_for_ip_address``.
    """

    def __init__(self, message: str, observed: Any = None) -> None:
        """
            Initialise the error.

            :param message: Multi-line error text.
            :param observed: The invalid observation made.

            :returns: ``None``
        """
        super().__init__(message)
        self.observed = observed
        return
