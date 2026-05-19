"""
    .. module:: eventfilter
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Filter spec consumed by :meth:`EventsGroup.stream`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from automojo.restclient.base.schemaobject import SchemaObject
from automojo.restclient.base.schemafield import Field


class EventFilter(SchemaObject):
    """
        Filter applied to the vCenter event stream.

        ``event_types`` and ``severities`` are list-valued; ``target_kind``
        and ``target_id`` constrain to events about a particular object;
        ``since`` is an inclusive lower bound on event timestamps.
    """
    event_types = Field(list, required=False)
    severities = Field(list, required=False)
    target_kind = Field(str, required=False)
    target_id = Field(str, required=False)
    since = Field(str, required=False)
