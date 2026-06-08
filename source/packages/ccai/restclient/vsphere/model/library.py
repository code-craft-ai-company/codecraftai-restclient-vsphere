"""
    .. module:: library
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Content-library DTOs for vSphere responses.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class LibraryItemSummary(SchemaObject):
    """
        Compact summary of a vSphere Content Library item.
    """
    item_id = Field(str, required=True)
    library_id = Field(str, required=True)
    name = Field(str, required=True)
    type = Field(str, required=False)
    description = Field(str, required=False)
    creation_time = Field(str, required=False)
    tags = Field(list, required=False)
