"""
    .. module:: powerstate
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: VM power-state enumeration.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from enum import Enum


class PowerState(str, Enum):
    """
        Power states reported by vSphere for a virtual machine.
    """
    POWERED_ON = "POWERED_ON"
    POWERED_OFF = "POWERED_OFF"
    SUSPENDED = "SUSPENDED"
