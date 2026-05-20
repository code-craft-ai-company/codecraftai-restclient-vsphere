"""
    .. module:: hvcgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Hybrid Linked Mode API group for :class:`VSphereClient`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Automation Mojo LLC"
__credits__ = []


from automojo.restclient.vsphere.apigroups.basegroup import BaseGroup


class HvcGroup(BaseGroup):
    """
        Hybrid Linked Mode operations.

        The legacy ``*Ext`` class in ``automojo-landscaping`` did not
        expose any public methods on this group; the structural
        migration is complete and feature methods will be added by
        downstream specs as needed (see ``vsphere-content-library-deploy``,
        ``vsphere-events-stream``, ``vsphere-linked-mode``,
        ``vsphere-inventory-helpers`` for the planned additions).
    """

    BASE_LEAF = "/api/vcenter/hvc"
