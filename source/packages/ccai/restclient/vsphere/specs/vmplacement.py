"""
    .. module:: vmplacement
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec describing where a new (or cloned) VM should reside.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class VmPlacementSpec(SchemaObject):
    """
        Placement coordinates for a new or cloned VM.
    """
    datacenter = Field(str, required=False)
    cluster = Field(str, required=False)
    host = Field(str, required=False)
    resource_pool = Field(str, required=False)
    folder = Field(str, required=False)
    datastore = Field(str, required=False)
