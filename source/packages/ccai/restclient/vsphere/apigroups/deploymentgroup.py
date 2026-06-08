"""
    .. module:: deploymentgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: vCenter deployment API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup


class DeploymentGroup(BaseGroup):
    """
        vCenter deployment operations.

        The legacy ``*Ext`` class in ``codecraftai-landscaping`` did not
        expose any public methods on this group; the structural
        migration is complete and feature methods will be added by
        downstream specs as needed (see ``vsphere-content-library-deploy``,
        ``vsphere-events-stream``, ``vsphere-linked-mode``,
        ``vsphere-inventory-helpers`` for the planned additions).
    """

    BASE_LEAF = "/api/vcenter/deployment"
