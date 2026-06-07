"""
    .. module:: contentdeploy
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec describing the runtime parameters for a Content
        Library OVF item deployment.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class ContentDeploySpec(SchemaObject):
    """
        Deployment-time parameters consumed by
        :meth:`ContentGroup.deploy_ovf_item`.
    """
    target_vm_name = Field(str, required=True)
    accept_all_eula = Field(bool, required=False)
    network_mappings = Field(dict, required=False)
    storage_provisioning = Field(str, required=False)
    additional_parameters = Field(list, required=False)
