"""
    .. module:: vmsnapshot
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec for creating a VM snapshot.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from automojo.restclient.base.schemaobject import SchemaObject
from automojo.restclient.base.schemafield import Field


class VmSnapshotSpec(SchemaObject):
    """
        Parameters used by the snapshot-create endpoint.
    """
    name = Field(str, required=True)
    description = Field(str, required=False)
    memory = Field(bool, required=False)
    quiesce = Field(bool, required=False)
