"""
    .. module:: vmstorage
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Storage-shape spec for VM creation requests.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from automojo.restclient.base.schemaobject import SchemaObject
from automojo.restclient.base.schemafield import Field


class VmDiskSpec(SchemaObject):
    """
        Single disk entry for a VM storage spec.
    """
    name = Field(str, required=False)
    capacity = Field(int, required=False)
    storage_policy = Field(str, required=False)


class VmStorageSpec(SchemaObject):
    """
        Aggregate storage shape for a new VM.
    """
    disks = Field(list, required=False)
    storage_policy = Field(str, required=False)
