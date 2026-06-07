"""
    .. module:: ovfdeploy
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Spec describing the runtime parameters for an OVF
        URL-based or local-file deployment via :class:`OvfGroup`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.base.schemaobject import SchemaObject
from ccai.restclient.base.schemafield import Field


class OvfDeploySpec(SchemaObject):
    """
        Deployment-time parameters consumed by
        :meth:`OvfGroup.deploy_from_url` and
        :meth:`OvfGroup.deploy_from_local_ovf`.
    """
    target_vm_name = Field(str, required=True)
    accept_all_eula = Field(bool, required=False)
    network_mappings = Field(dict, required=False)
    storage_provisioning = Field(str, required=False)
    annotation = Field(str, required=False)
    additional_parameters = Field(list, required=False)
