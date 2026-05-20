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


def _coalesce_attr(*, source: object, names: tuple, default: float) -> float:
    """
        Return the first present, non-None attribute of ``source`` named
        in ``names``, falling back to ``default``.

        :param source: The object to inspect.
        :param names: Candidate attribute names, in priority order.
        :param default: Value returned when no candidate is present.

        :returns: The resolved value.
    """
    rtnval = default
    for name in names:
        if hasattr(source, name):
            value = getattr(source, name)
            if value is not None:
                rtnval = value
                break
    return rtnval


def vsphere_aspects_from_aspects(*, aspects: object) -> AspectsVSphere:
    """
        Adapt any ``Aspects``-shaped object into an :class:`AspectsVSphere`.

        A provisioning-layer caller carries a ``ProvisioningAspects`` (or
        another aspects bundle) whose timeout / interval fields are named
        differently from those on :class:`AspectsVSphere`.  This adapter
        maps the common fields so the bundle can be forwarded straight
        into the vSphere client surface.

        Field mapping (first present wins):
          * completion_timeout  <- completion_timeout | verify_timeout | timeout
          * completion_interval <- completion_interval | verify_interval | interval

        When ``aspects`` is already an :class:`AspectsVSphere` it is
        returned unchanged.

        :param aspects: Any aspects-shaped object (including
            ``ProvisioningAspects``) or ``None``.

        :returns: An :class:`AspectsVSphere` instance.
    """
    if isinstance(aspects, AspectsVSphere):
        rtnval = aspects
        return rtnval

    if aspects is None:
        rtnval = AspectsVSphere()
        return rtnval

    completion_timeout = _coalesce_attr(
        source=aspects,
        names=("completion_timeout", "verify_timeout", "timeout"),
        default=30.0,
    )
    completion_interval = _coalesce_attr(
        source=aspects,
        names=("completion_interval", "verify_interval", "interval"),
        default=2.0,
    )

    logger = None
    if hasattr(aspects, "logger"):
        logger = getattr(aspects, "logger")

    rtnval = AspectsVSphere(
        completion_timeout=completion_timeout,
        completion_interval=completion_interval,
        logger=logger,
    )
    return rtnval


def _from_aspects_classmethod(cls, aspects: object) -> AspectsVSphere:
    """
        Classmethod body for :meth:`AspectsVSphere.from_aspects`.

        :param cls: The :class:`AspectsVSphere` class object.
        :param aspects: Any aspects-shaped object or ``None``.

        :returns: An :class:`AspectsVSphere` instance.
    """
    _ = cls
    rtnval = vsphere_aspects_from_aspects(aspects=aspects)
    return rtnval


AspectsVSphere.from_aspects = classmethod(_from_aspects_classmethod)


DEFAULT_VSPHERE_ASPECTS = AspectsVSphere()
