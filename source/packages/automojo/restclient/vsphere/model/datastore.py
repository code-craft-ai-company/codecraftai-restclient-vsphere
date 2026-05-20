"""
    .. module:: datastore
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Datastore DTOs for vSphere.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from typing import Optional

from automojo.restclient.base.schemaobject import SchemaObject
from automojo.restclient.base.schemafield import Field


class DatastoreSummary(SchemaObject):
    """
        Compact datastore summary.
    """
    name = Field(str, required=True)
    datastore = Field(str, required=True)
    type = Field(str, required=False)
    capacity = Field(int, required=False)
    free_space = Field(int, required=False)


class DatastoreInfo(SchemaObject):
    """
        Full datastore detail including accessibility flags.
    """
    name = Field(str, required=True)
    datastore = Field(str, required=True)
    type = Field(str, required=False)
    capacity = Field(int, required=False)
    free_space = Field(int, required=False)
    accessible = Field(bool, required=False)
    multiple_host_access = Field(bool, required=False)
    thin_provisioning_supported = Field(bool, required=False)
