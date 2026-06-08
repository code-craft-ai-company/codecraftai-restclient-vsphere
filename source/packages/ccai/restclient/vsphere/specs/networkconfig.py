"""
    .. module:: networkconfig
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Per-NIC network configuration record composed by
        :class:`VmGuestCustomizationSpec`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from enum import Enum

from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class NetworkMode(str, Enum):
    """
        Per-NIC address acquisition mode.
    """
    DHCP = "DHCP"
    STATIC = "STATIC"


class NetworkConfig(SchemaObject):
    """
        Per-NIC network configuration entry.
    """
    nic_index = Field(int, required=True)
    mode = Field(str, required=True)
    ipv4_address = Field(str, required=False)
    ipv4_prefix = Field(int, required=False)
    ipv4_gateway = Field(str, required=False)
    ipv6_address = Field(str, required=False)
    ipv6_prefix = Field(int, required=False)
    ipv6_gateway = Field(str, required=False)
