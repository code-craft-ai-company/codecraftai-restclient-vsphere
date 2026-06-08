"""
    .. module:: vmguestcustomization
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec for guest-OS customization applied at clone / first
        boot.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class VmGuestCustomizationSpec(SchemaObject):
    """
        Guest customisation payload used at clone / first-boot time.
    """
    hostname = Field(str, required=True)
    dns_servers = Field(list, required=False)
    dns_search = Field(list, required=False)
    network_configs = Field(list, required=False)
    ssh_authorized_keys = Field(list, required=False)
    run_command_scripts = Field(list, required=False)
