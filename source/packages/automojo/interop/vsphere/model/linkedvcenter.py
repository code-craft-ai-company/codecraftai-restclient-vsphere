"""
    .. module:: linkedvcenter
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: DTO describing a linked-mode peer vCenter.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from automojo.restclient.base.schemaobject import SchemaObject
from automojo.restclient.base.schemafield import Field


class LinkedVCenterRecord(SchemaObject):
    """
        Record of a vCenter participating in Linked Mode (HVC).
    """
    uuid = Field(str, required=True)
    hostname = Field(str, required=True)
    version = Field(str, required=False)
    build = Field(str, required=False)
    is_local = Field(bool, required=False)
