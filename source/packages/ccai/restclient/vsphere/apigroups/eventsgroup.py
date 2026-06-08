"""
    .. module:: eventsgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Events API group for :class:`VSphereClient`.  The legacy
        ext-module surface did not include events; this group is new.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from http import HTTPStatus
from typing import Callable, List, Optional

from ccai.errors.raising import raise_for_http_status

from ccai.restclient.vsphere.apigroups.basegroup import BaseGroup
from ccai.restclient.vsphere.apigroups.eventstream import (
    DEFAULT_EVENT_BUFFER_LIMIT,
    EventStream,
)
from ccai.restclient.vsphere.aspectsvsphere import (
    AspectsVSphere,
    DEFAULT_VSPHERE_ASPECTS,
)
from ccai.restclient.vsphere.specs.eventfilter import EventFilter


class EventsGroup(BaseGroup):
    """
        Events operations.

        Provides ``stream(filter, aspects)`` which returns an
        :class:`EventStream` iterator over vCenter events.
    """

    BASE_LEAF = "/api/cis/tasks/events"

    def stream(
        self,
        *,
        filter: EventFilter,
        aspects: AspectsVSphere = DEFAULT_VSPHERE_ASPECTS,
        buffer_limit: int = DEFAULT_EVENT_BUFFER_LIMIT,
        fetcher: Optional[Callable[[Optional[str], EventFilter], List[dict]]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
    ) -> EventStream:
        """
            Return an iterator that yields :class:`EventRecord` entries
            matching ``filter`` as they arrive from vCenter.

            ``fetcher`` is the injection seam used by tests to drive
            scripted batches.  When omitted, the default fetcher issues
            a long-poll GET against the vCenter events endpoint.

            :param filter: :class:`EventFilter` to apply.
            :param aspects: Behaviour controls.
            :param buffer_limit: Local backpressure buffer cap.
            :param fetcher: Optional injected callable.
            :param sleeper: Optional override for ``time.sleep``.

            :returns: An :class:`EventStream`.
        """
        if fetcher is None:
            def _default_fetcher(
                last_seen: Optional[str],
                active_filter: EventFilter,
            ) -> List[dict]:
                inner_rtnval = self._fetch_events(
                    last_seen=last_seen,
                    active_filter=active_filter,
                    aspects=aspects,
                )
                return inner_rtnval
            fetcher = _default_fetcher

        rtnval = EventStream(
            fetcher=fetcher,
            filter=filter,
            poll_interval=aspects.completion_interval,
            buffer_limit=buffer_limit,
            sleeper=sleeper,
            logger=aspects.logger,
        )
        return rtnval

    def _fetch_events(
        self,
        *,
        last_seen: Optional[str],
        active_filter: EventFilter,
        aspects: AspectsVSphere,
    ) -> List[dict]:
        """
            Default fetcher — issues a single GET to the events leaf.

            :param last_seen: The id of the last event observed (used as
                a server-side cursor when supplied).
            :param active_filter: The active :class:`EventFilter`.
            :param aspects: Behaviour controls.

            :returns: List of raw event dicts.
        """
        client = self.client
        url = client.build_url(leaf=self.BASE_LEAF)
        params = {}
        if last_seen is not None:
            params["after"] = last_seen
        session = client.ensure_session(aspects=aspects)
        resp = session.get(url, params=params, timeout=aspects.completion_timeout)
        if resp.status_code != HTTPStatus.OK:
            raise_for_http_status(
                resp.status_code, resp.content, url, context="EventsGroup._fetch_events",
            )
        body = resp.json()
        if isinstance(body, list):
            rtnval = body
        else:
            rtnval = []
        return rtnval
