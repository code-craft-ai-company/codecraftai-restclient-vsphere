"""
    .. module:: vmpoweraction
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec naming the discrete power action to apply to a VM.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class VmPowerActionSpec(SchemaObject):
    """
        Names a single power-management action.
    """
    action = Field(str, required=True)
