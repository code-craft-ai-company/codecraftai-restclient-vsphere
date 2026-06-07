"""
    .. module:: summary
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Typed summary DTOs for the vSphere inventory hierarchy.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Optional

from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class DatacenterSummary(SchemaObject):
    """
        Compact summary of a vSphere datacenter.
    """
    name = Field(str, required=True)
    datacenter = Field(str, required=True)
    datastore_folder = Field(str, required=False)
    host_folder = Field(str, required=False)
    network_folder = Field(str, required=False)
    vm_folder = Field(str, required=False)


class FolderSummary(SchemaObject):
    """
        Compact summary of a vSphere folder.
    """
    name = Field(str, required=True)
    folder = Field(str, required=True)
    type = Field(str, required=False)


class ClusterSummary(SchemaObject):
    """
        Compact summary of a vSphere cluster.
    """
    name = Field(str, required=True)
    cluster = Field(str, required=True)
    ha_enabled = Field(bool, required=False)
    drs_enabled = Field(bool, required=False)


class HostSummary(SchemaObject):
    """
        Compact summary of an ESXi host.
    """
    name = Field(str, required=True)
    host = Field(str, required=True)
    connection_state = Field(str, required=False)
    power_state = Field(str, required=False)
