"""
    .. module:: event
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Event record DTO returned by the events api group.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class EventRecord(SchemaObject):
    """
        A single event entry from vCenter's event stream.
    """
    id = Field(str, required=True)
    type = Field(str, required=True)
    timestamp = Field(str, required=False)
    severity = Field(str, required=False)
    message = Field(str, required=False)
    user = Field(str, required=False)
    target = Field(dict, required=False)
