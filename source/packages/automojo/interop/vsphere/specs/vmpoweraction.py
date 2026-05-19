"""
    .. module:: vmpoweraction
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec naming the discrete power action to apply to a VM.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from automojo.restclient.base.schemaobject import SchemaObject
from automojo.restclient.base.schemafield import Field


class VmPowerActionSpec(SchemaObject):
    """
        Names a single power-management action.
    """
    action = Field(str, required=True)
