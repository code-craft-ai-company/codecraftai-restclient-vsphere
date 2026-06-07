"""
    .. module:: ovf
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: OVF descriptor and deploy-result DTOs.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Optional

from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class OvfDescriptor(SchemaObject):
    """
        Parsed OVF descriptor fields.
    """
    name = Field(str, required=True)
    vendor = Field(str, required=False)
    version = Field(str, required=False)
    eula = Field(list, required=False)
    properties = Field(list, required=False)
    networks = Field(list, required=False)


class OvfDeployResult(SchemaObject):
    """
        Result of an OVF deploy operation.
    """
    resource_id = Field(str, required=False)
    deployable = Field(bool, required=False)
    error = Field(dict, required=False)
