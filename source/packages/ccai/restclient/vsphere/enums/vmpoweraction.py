"""
    .. module:: vmpoweraction
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: VM power-action enumeration consumed by
        :class:`VmPowerActionSpec`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from enum import Enum


class VmPowerAction(str, Enum):
    """
        Discrete power-management actions supported by vSphere.
    """
    POWER_ON = "POWER_ON"
    POWER_OFF = "POWER_OFF"
    SUSPEND = "SUSPEND"
    RESET = "RESET"
    GUEST_SHUTDOWN = "GUEST_SHUTDOWN"
    GUEST_REBOOT = "GUEST_REBOOT"
