"""
    .. module:: vspherefilterstate
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Provides :class:`VSphereFilterState`, the optional context
        object held by :class:`VSphereClient` for scoping group calls to
        a working datacenter / folder / cluster / resource pool.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Optional


class VSphereFilterState:
    """
        Holds working filter context (datacenter, folder, cluster,
        resource pool) that group methods may consult when callers do
        not supply explicit identifiers.
    """

    def __init__(
        self,
        *,
        datacenter: Optional[str] = None,
        folder: Optional[str] = None,
        cluster: Optional[str] = None,
        resource_pool: Optional[str] = None,
    ) -> None:
        """
            Initialise a filter-state record.

            :param datacenter: Working datacenter id, or ``None``.
            :param folder: Working folder id, or ``None``.
            :param cluster: Working cluster id, or ``None``.
            :param resource_pool: Working resource pool id, or ``None``.

            :returns: ``None``
        """
        self._datacenter = datacenter
        self._folder = folder
        self._cluster = cluster
        self._resource_pool = resource_pool
        return

    @property
    def datacenter(self) -> Optional[str]:
        """
            Working datacenter identifier.

            :returns: The datacenter id or ``None``.
        """
        rtnval = self._datacenter
        return rtnval

    @property
    def folder(self) -> Optional[str]:
        """
            Working folder identifier.

            :returns: The folder id or ``None``.
        """
        rtnval = self._folder
        return rtnval

    @property
    def cluster(self) -> Optional[str]:
        """
            Working cluster identifier.

            :returns: The cluster id or ``None``.
        """
        rtnval = self._cluster
        return rtnval

    @property
    def resource_pool(self) -> Optional[str]:
        """
            Working resource pool identifier.

            :returns: The resource pool id or ``None``.
        """
        rtnval = self._resource_pool
        return rtnval

    def is_empty(self) -> bool:
        """
            Indicates if every component of the filter state is unset.

            :returns: ``True`` when no filter slot is populated.
        """
        rtnval = (
            self._datacenter is None
            and self._folder is None
            and self._cluster is None
            and self._resource_pool is None
        )
        return rtnval
