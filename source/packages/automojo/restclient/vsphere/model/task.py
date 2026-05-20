"""
    .. module:: task
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Re-export ``TaskInfo`` from the task-handle module so the
        DTO surface area is symmetric with the other ``model/`` modules.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from automojo.restclient.vsphere.vspheretaskhandle import TaskInfo, TaskState


__all__ = ["TaskInfo", "TaskState"]
