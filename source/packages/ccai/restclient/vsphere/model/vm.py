"""
    .. module:: vm
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Virtual-machine DTOs for vSphere responses.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Optional

from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class VirtualMachineSummary(SchemaObject):
    """
        Compact VM summary returned by ``GET /api/vcenter/vm`` listings.
    """
    name = Field(str, required=True)
    vm = Field(str, required=True)
    power_state = Field(str, required=False)
    cpu_count = Field(int, required=False)
    memory_size_MiB = Field(int, required=False)


class VirtualMachineInfo(SchemaObject):
    """
        Full VM detail returned by ``GET /api/vcenter/vm/{vm}``.

        Fields beyond the core identity slots are captured as raw
        dictionaries to keep this DTO useful without locking the entire
        hardware tree to the legacy snapshot.  The dedicated hardware
        DTOs live alongside the spec types in
        ``ccai.restclient.vsphere.specs`` and may be applied by future
        callers when stronger typing is needed.
    """
    name = Field(str, required=True)
    vm = Field(str, required=True)
    power_state = Field(str, required=False)
    guest_OS = Field(str, required=False)
    cpu = Field(dict, required=False)
    memory = Field(dict, required=False)
    boot = Field(dict, required=False)
    hardware = Field(dict, required=False)
    disks = Field(dict, required=False)
    nics = Field(dict, required=False)
    cdroms = Field(dict, required=False)
    floppies = Field(dict, required=False)
    nvme_adapters = Field(dict, required=False)
    sata_adapters = Field(dict, required=False)
    scsi_adapters = Field(dict, required=False)
    serial_ports = Field(dict, required=False)
    parallel_ports = Field(dict, required=False)
    identity = Field(dict, required=False)
    instant_clone_frozen = Field(bool, required=False)
