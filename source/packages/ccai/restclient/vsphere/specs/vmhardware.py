"""
    .. module:: vmhardware
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Hardware-shape spec for VM creation requests.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class VmHardwareSpec(SchemaObject):
    """
        CPU / memory / hardware-version coordinates for a new VM.
    """
    cpu_count = Field(int, required=False)
    cores_per_socket = Field(int, required=False)
    memory_mib = Field(int, required=False)
    hardware_version = Field(str, required=False)
