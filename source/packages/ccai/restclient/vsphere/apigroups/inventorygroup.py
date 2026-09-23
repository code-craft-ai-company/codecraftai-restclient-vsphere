"""
    .. module:: inventorygroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Inventory-helpers API group for :class:`VSphereClient`.
        The helpers compose existing ``*Group`` methods (``Vm.list``,
        ``Datastore.list``, ``Host.list``) and apply deterministic
        selection rules so that the provisioning engine's ``apply`` is
        idempotent against an unchanged inventory.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


import os

from typing import List, Optional

from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup
from ccai.restclient.vsphere.apigroups.inventoryerrors import (
    VSphereAmbiguousResolutionError,
    VSphereResourceNotFoundError,
)
from ccai.restclient.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from ccai.restclient.vsphere.model.datastore import DatastoreSummary
from ccai.restclient.vsphere.model.summary import HostSummary
from ccai.restclient.vsphere.model.vm import VirtualMachineSummary


_BYTES_PER_GB = 1024 * 1024 * 1024


class InventoryGroup(BaseGroup):
    """
        Inventory-helper queries.

        Selection determinism is the central invariant — every helper
        that selects a single record from a candidate set applies a
        total ordering on the candidates, documented in the helper's
        docstring and verified by hypothesis property tests.
    """

    BASE_LEAF = "/api/vcenter/inventory"

    def find_vm_by_name(
        self,
        *,
        name: str,
        candidates: Optional[List[VirtualMachineSummary]] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> VirtualMachineSummary:
        """
            Resolve a VM name to a single :class:`VirtualMachineSummary`.

            Uniqueness rule: the match must be unique across the search
            scope.  Multiple matches raise
            :class:`VSphereAmbiguousResolutionError`; zero matches raise
            :class:`VSphereResourceNotFoundError`.  The candidate set
            defaults to ``client.Vm.list``; tests inject an explicit
            list via ``candidates`` to bypass HTTP.

            :param name: VM display name.
            :param candidates: Optional candidate VM list (injected by
                tests; ``None`` means call ``client.Vm.list``).
            :param aspects: Behaviour controls.

            :returns: A :class:`VirtualMachineSummary`.

            :raises: VSphereResourceNotFoundError,
                VSphereAmbiguousResolutionError
        """
        records = self._resolve_vm_candidates(candidates=candidates, aspects=aspects)
        matches: List[VirtualMachineSummary] = []
        for record in records:
            if getattr(record, "name", None) == name:
                matches.append(record)

        if len(matches) == 0:
            err_msg_lines = [
                "No VM matched the requested name.",
                "NAME: {}".format(name),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise VSphereResourceNotFoundError(err_msg)

        if len(matches) > 1:
            err_msg_lines = [
                "Multiple VMs matched the requested name.",
                "NAME: {}".format(name),
                "COUNT: {}".format(len(matches)),
            ]
            for cand in matches:
                err_msg_lines.append(
                    "    {}: vm={}".format(
                        getattr(cand, "name", "?"), getattr(cand, "vm", "?"),
                    ),
                )
            err_msg = os.linesep.join(err_msg_lines)
            raise VSphereAmbiguousResolutionError(err_msg, candidates=matches)

        rtnval = matches[0]
        return rtnval

    def find_vm_by_tag(
        self,
        *,
        tag: str,
        tag_lookup: Optional[dict] = None,
        candidates: Optional[List[VirtualMachineSummary]] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> List[VirtualMachineSummary]:
        """
            Return all VMs carrying the given tag, ordered by
            ``(name ASC, vm ASC)`` for stability.

            ``tag_lookup`` is a mapping ``vm_id -> List[str]`` of tag
            ids; supplied either by the caller's tag-resolution pass or
            by tests bypassing HTTP.  When ``tag_lookup`` is ``None``
            the helper returns an empty list (the caller has not
            resolved tags) — this is intentional: tag resolution is
            owned by ``TaggingGroup`` and must be performed before this
            helper can produce a useful result.

            :param tag: Tag identifier to match.
            :param tag_lookup: Mapping from VM id to its list of tag ids.
            :param candidates: Optional injected candidate VM list.
            :param aspects: Behaviour controls.

            :returns: List of matching :class:`VirtualMachineSummary`.
        """
        if tag_lookup is None:
            rtnval: List[VirtualMachineSummary] = []
            return rtnval

        records = self._resolve_vm_candidates(candidates=candidates, aspects=aspects)
        matches: List[VirtualMachineSummary] = []
        for record in records:
            vm_id = getattr(record, "vm", None)
            if vm_id is None:
                continue
            tags = tag_lookup.get(vm_id)
            if tags is None:
                continue
            if tag in tags:
                matches.append(record)

        def _sort_key(rec: VirtualMachineSummary):
            inner_rtnval = (
                "" if getattr(rec, "name", None) is None else getattr(rec, "name"),
                "" if getattr(rec, "vm", None) is None else getattr(rec, "vm"),
            )
            return inner_rtnval

        matches.sort(key=_sort_key)
        rtnval = matches
        return rtnval

    def find_datastore_with_free_gb(
        self,
        *,
        min_free_gb: float,
        candidates: Optional[List[DatastoreSummary]] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> DatastoreSummary:
        """
            Pick a datastore with at least ``min_free_gb`` of free space.

            Selection rule (total order):
                primary: ``free_space_gb`` DESC
                secondary: ``name`` ASC
                tertiary: ``datastore`` (id) ASC

            :param min_free_gb: Minimum free space in GB.
            :param candidates: Optional injected candidate list.
            :param aspects: Behaviour controls.

            :returns: A :class:`DatastoreSummary` from the candidate set.

            :raises: VSphereResourceNotFoundError
        """
        records = self._resolve_datastore_candidates(
            candidates=candidates, aspects=aspects,
        )

        eligible: List[DatastoreSummary] = []
        for record in records:
            free_bytes = getattr(record, "free_space", None)
            if free_bytes is None:
                continue
            free_gb = float(free_bytes) / float(_BYTES_PER_GB)
            if free_gb >= min_free_gb:
                eligible.append(record)

        if len(eligible) == 0:
            err_msg_lines = [
                "No datastore meets the free-space criterion.",
                "MIN_FREE_GB: {}".format(min_free_gb),
                "CANDIDATES: {}".format(len(records)),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise VSphereResourceNotFoundError(err_msg)

        def _sort_key(rec: DatastoreSummary):
            free_bytes_local = getattr(rec, "free_space", 0)
            free_gb_local = float(free_bytes_local) / float(_BYTES_PER_GB)
            name_val = "" if getattr(rec, "name", None) is None else getattr(rec, "name")
            id_val = "" if getattr(rec, "datastore", None) is None else getattr(rec, "datastore")
            inner_rtnval = (-free_gb_local, name_val, id_val)
            return inner_rtnval

        eligible.sort(key=_sort_key)
        rtnval = eligible[0]
        return rtnval

    def pick_least_loaded_host(
        self,
        *,
        cluster: str,
        host_loads: Optional[dict] = None,
        candidates: Optional[List[HostSummary]] = None,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
    ) -> HostSummary:
        """
            Pick the least-loaded host in a cluster.

            "Load" is defined as
                ``cpu_usage_percent * 0.6 + memory_usage_percent * 0.4``.

            Selection rule (total order):
                primary: ``load`` ASC
                secondary: ``name`` ASC
                tertiary: ``host`` (id) ASC

            Connectivity filter: only hosts whose ``connection_state``
            is ``CONNECTED`` (or missing — treated as connected for
            test fixtures that do not populate the field) are
            considered.

            :param cluster: Cluster identifier (used only for error
                context; the candidate filtering is by ``host_loads``
                or the injected ``candidates`` list).
            :param host_loads: Optional mapping ``host_id -> dict`` with
                ``cpu_usage_percent`` and ``memory_usage_percent``
                fields.  Tests inject this; missing entries default to
                ``(0.0, 0.0)``.
            :param candidates: Optional injected candidate host list.
            :param aspects: Behaviour controls.

            :returns: A :class:`HostSummary`.

            :raises: VSphereResourceNotFoundError
        """
        records = self._resolve_host_candidates(candidates=candidates, aspects=aspects)
        if host_loads is None:
            host_loads = {}

        connected: List[HostSummary] = []
        for record in records:
            conn_state = getattr(record, "connection_state", None)
            if conn_state is None or conn_state == "CONNECTED":
                connected.append(record)

        if len(connected) == 0:
            err_msg_lines = [
                "Cluster has no connected hosts.",
                "CLUSTER: {}".format(cluster),
            ]
            err_msg = os.linesep.join(err_msg_lines)
            raise VSphereResourceNotFoundError(err_msg)

        def _sort_key(rec: HostSummary):
            host_id = getattr(rec, "host", None)
            load_entry = host_loads.get(host_id) if host_id is not None else None
            if load_entry is None:
                cpu = 0.0
                mem = 0.0
            else:
                cpu = float(load_entry.get("cpu_usage_percent", 0.0))
                mem = float(load_entry.get("memory_usage_percent", 0.0))
            load = (cpu * 0.6) + (mem * 0.4)
            name_val = "" if getattr(rec, "name", None) is None else getattr(rec, "name")
            id_val = "" if host_id is None else host_id
            inner_rtnval = (load, name_val, id_val)
            return inner_rtnval

        connected.sort(key=_sort_key)
        rtnval = connected[0]
        return rtnval

    # ------------------------------------------------------------------
    # Candidate resolvers
    # ------------------------------------------------------------------

    def _resolve_vm_candidates(
        self,
        *,
        candidates: Optional[List[VirtualMachineSummary]],
        aspects: AspectsVSphere,
    ) -> List[VirtualMachineSummary]:
        """
            Return the candidate VM list — either the injected list or
            the result of ``client.Vm.list``.

            :param candidates: Optional injected list.
            :param aspects: Behaviour controls.

            :returns: The candidate list.
        """
        if candidates is not None:
            rtnval = list(candidates)
            return rtnval
        rtnval = self.client.Vm.list(aspects=aspects)
        return rtnval

    def _resolve_datastore_candidates(
        self,
        *,
        candidates: Optional[List[DatastoreSummary]],
        aspects: AspectsVSphere,
    ) -> List[DatastoreSummary]:
        """
            Return the candidate datastore list.

            :param candidates: Optional injected list.
            :param aspects: Behaviour controls.

            :returns: The candidate list.
        """
        if candidates is not None:
            rtnval = list(candidates)
            return rtnval
        rtnval = self.client.Datastore.list(aspects=aspects)
        return rtnval

    def _resolve_host_candidates(
        self,
        *,
        candidates: Optional[List[HostSummary]],
        aspects: AspectsVSphere,
    ) -> List[HostSummary]:
        """
            Return the candidate host list.

            :param candidates: Optional injected list.
            :param aspects: Behaviour controls.

            :returns: The candidate list.
        """
        if candidates is not None:
            rtnval = list(candidates)
            return rtnval
        rtnval = self.client.Host.list(aspects=aspects)
        return rtnval
