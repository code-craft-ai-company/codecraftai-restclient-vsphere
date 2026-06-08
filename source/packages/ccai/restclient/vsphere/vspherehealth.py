"""
    .. module:: vspherehealth
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Provides :class:`VSphereHealth`, the dataclass returned
        by :meth:`VSphereClient.health` describing connectivity and
        session validity.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from dataclasses import dataclass


@dataclass
class VSphereHealth:
    """
        Snapshot of vCenter reachability and session validity.

        :param reachable: ``True`` when vCenter responded to a probe.
        :param session_valid: ``True`` when the cached session id is
            accepted by vCenter.
        :param time_skew_seconds: Approximate clock skew in seconds
            between client and server.
    """
    reachable: bool
    session_valid: bool
    time_skew_seconds: float
