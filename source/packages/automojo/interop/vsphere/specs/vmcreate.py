"""
    .. module:: vmcreate
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Aggregate spec for vSphere VM creation.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from automojo.restclient.base.schemaobject import SchemaObject
from automojo.restclient.base.schemafield import Field


class VmCreateSpec(SchemaObject):
    """
        Aggregate parameters used by ``VmGroup.create``.
    """
    name = Field(str, required=True)
    guest_OS = Field(str, required=True)
    placement = Field(dict, required=False)
    hardware = Field(dict, required=False)
    storage = Field(dict, required=False)
    networks = Field(list, required=False)
