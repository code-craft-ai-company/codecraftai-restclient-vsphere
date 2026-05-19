"""
    .. module:: aspectsvsphere
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Provides the ``AspectsVSphere`` subclass and the
        ``DEFAULT_VSPHERE_ASPECTS`` instance used by every call on
        :class:`VSphereClient` and its API groups.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


import logging

from automojo.restclient.base.aspectsrest import (
    AspectsRest,
    ActionPattern,
    LoggingPattern,
)


class AspectsVSphere(AspectsRest):
    """
        vSphere-specialised :class:`AspectsRest`.

        The class exists so that callers can write
        ``aspects: AspectsVSphere`` for clarity at call sites and so that
        future vSphere-specific behaviour can be added without churning
        the public type signature on every group method.
    """

    def __init__(
        self,
        *,
        action_pattern: ActionPattern = ActionPattern.SINGLE_CALL,
        completion_timeout: float = 30.0,
        completion_interval: float = 2.0,
        connection_timeout: float = 16.0,
        inactivity_timeout: float = 30.0,
        monitor_delay: float = 30.0,
        logging_pattern: int = LoggingPattern.ALL_RESULTS,
        retry_logging_interval: int = 5,
        must_connect: bool = False,
        logger: logging.Logger = None,
    ) -> None:
        """
            Initialise a vSphere-flavoured aspects bundle.

            :param action_pattern: Action pattern for the call.
            :param completion_timeout: Overall completion timeout in seconds.
            :param completion_interval: Poll interval for waiters in seconds.
            :param connection_timeout: TCP connection establishment timeout.
            :param inactivity_timeout: Per-read inactivity timeout.
            :param monitor_delay: Delay before background monitoring begins.
            :param logging_pattern: Logging pattern controlling verbosity.
            :param retry_logging_interval: Cadence at which retry attempts log.
            :param must_connect: Whether a connection failure is fatal.
            :param logger: Optional logger override.

            :returns: ``None``
        """
        super().__init__(
            action_pattern=action_pattern,
            completion_timeout=completion_timeout,
            completion_interval=completion_interval,
            connection_timeout=connection_timeout,
            inactivity_timeout=inactivity_timeout,
            monitor_delay=monitor_delay,
            logging_pattern=logging_pattern,
            retry_logging_interval=retry_logging_interval,
            must_connect=must_connect,
            logger=logger,
        )
        return


DEFAULT_VSPHERE_ASPECTS = AspectsVSphere()
