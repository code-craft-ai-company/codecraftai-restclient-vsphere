"""
    .. module:: vmclone
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec for cloning an existing VM.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from automojo.restclient.base.schemaobject import SchemaObject
from automojo.restclient.base.schemafield import Field


class VmCloneSpec(SchemaObject):
    """
        Parameters used by ``VmGroup.clone``.
    """
    source_vm_id = Field(str, required=True)
    target_name = Field(str, required=True)
    placement = Field(dict, required=False)
    power_on_after = Field(bool, required=False)
    customization_spec_ref = Field(str, required=False)
