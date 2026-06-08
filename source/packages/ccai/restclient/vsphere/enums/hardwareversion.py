"""
    .. module:: hardwareversion
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: vSphere virtual hardware version enum.  Migrated from
        the legacy ``metasphere/vmhardware.py``.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from enum import Enum


class HardwareVersion(str, Enum):
    """
        VMware virtual hardware versions ``VMX_03`` through ``VMX_20``.
    """
    VMX_03 = "VMX_03"
    VMX_04 = "VMX_04"
    VMX_06 = "VMX_06"
    VMX_07 = "VMX_07"
    VMX_08 = "VMX_08"
    VMX_09 = "VMX_09"
    VMX_10 = "VMX_10"
    VMX_11 = "VMX_11"
    VMX_12 = "VMX_12"
    VMX_13 = "VMX_13"
    VMX_14 = "VMX_14"
    VMX_15 = "VMX_15"
    VMX_16 = "VMX_16"
    VMX_17 = "VMX_17"
    VMX_18 = "VMX_18"
    VMX_19 = "VMX_19"
    VMX_20 = "VMX_20"
    VMX_21 = "VMX_21"
