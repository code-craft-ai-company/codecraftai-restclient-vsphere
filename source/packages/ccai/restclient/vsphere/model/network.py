"""
    .. module:: network
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Network DTOs for vSphere portgroup and DVS responses.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class NetworkSummary(SchemaObject):
    """
        Compact summary of a vSphere network.
    """
    name = Field(str, required=True)
    network = Field(str, required=True)
    type = Field(str, required=False)


class DistributedSwitchSummary(SchemaObject):
    """
        Compact summary of a vSphere Distributed Switch.
    """
    name = Field(str, required=True)
    switch = Field(str, required=True)
    uuid = Field(str, required=False)
    version = Field(str, required=False)
