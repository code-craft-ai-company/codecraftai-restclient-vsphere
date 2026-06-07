"""
    .. module:: eventstream
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Iterator class returned by :meth:`EventsGroup.stream`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


import logging
import time

from collections import deque
from typing import Any, Callable, Deque, List, Optional

from ccai.restclient.vsphere.model.event import EventRecord
from ccai.restclient.vsphere.specs.eventfilter import EventFilter


DEFAULT_EVENT_BUFFER_LIMIT = 1000


class EventStream:
    """
        Iterator over vCenter events.

        ``__iter__`` returns ``self``; ``__next__`` returns the next
        :class:`EventRecord` (driving a poll round when the local buffer
        is empty); ``close`` halts polling deterministically; the
        ``dropped_count`` property exposes the count of events shed by
        the backpressure rule.
    """

    def __init__(
        self,
        *,
        fetcher: Callable[[Optional[str], EventFilter], List[dict]],
        filter: EventFilter,
        poll_interval: float,
        buffer_limit: int = DEFAULT_EVENT_BUFFER_LIMIT,
        sleeper: Optional[Callable[[float], None]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
            Construct an event-stream iterator.

            :param fetcher: Callable invoked as ``fetcher(last_seen,
                filter)`` that returns the next batch of raw event
                dicts.  Injected so tests can drive scripted batches.
            :param filter: An :class:`EventFilter` instance.
            :param poll_interval: Seconds to sleep between empty polls.
            :param buffer_limit: Maximum events held in the local
                buffer; older entries are dropped when full.
            :param sleeper: Optional override for ``time.sleep``;
                injected by tests.
            :param logger: Optional structured logger override.

            :returns: ``None``
        """
        self._fetcher = fetcher
        self._filter = filter
        self._poll_interval = poll_interval
        self._buffer_limit = buffer_limit
        self._sleeper = sleeper if sleeper is not None else time.sleep
        self._logger = logger if logger is not None else logging.getLogger(
            "ccai.restclient.vsphere.events",
        )
        self._buffer: Deque[EventRecord] = deque()
        self._closed = False
        self._dropped_count = 0
        self._last_seen: Optional[str] = None
        return

    @property
    def dropped_count(self) -> int:
        """
            Count of events shed by the backpressure rule.

            :returns: The integer drop counter.
        """
        rtnval = self._dropped_count
        return rtnval

    @property
    def closed(self) -> bool:
        """
            Indicates if the stream has been closed.

            :returns: ``True`` after :meth:`close` has been called.
        """
        rtnval = self._closed
        return rtnval

    def __iter__(self) -> "EventStream":
        return self

    def __enter__(self) -> "EventStream":
        return self

    def __exit__(self, exc_type, exc_inst, exc_tb) -> None:
        self.close()
        return None

    def __next__(self) -> EventRecord:
        """
            Return the next event, polling as needed.

            :returns: An :class:`EventRecord`.

            :raises: StopIteration
        """
        while True:
            if self._closed:
                raise StopIteration

            if len(self._buffer) > 0:
                rtnval = self._buffer.popleft()
                return rtnval

            raw_batch = self._fetcher(self._last_seen, self._filter)

            if raw_batch is None or len(raw_batch) == 0:
                if self._closed:
                    raise StopIteration
                self._sleeper(self._poll_interval)
                continue

            self._ingest_batch(batch=raw_batch)

    def close(self) -> None:
        """
            Halt polling.  Subsequent ``__next__`` calls drain the
            local buffer and then raise :class:`StopIteration`.

            :returns: ``None``
        """
        self._closed = True
        return None

    def _ingest_batch(self, *, batch: List[dict]) -> None:
        """
            Convert raw event dicts to :class:`EventRecord`, apply
            client-side filtering, and append to the buffer (enforcing
            the buffer limit).

            :param batch: Raw event dicts from the fetcher.

            :returns: ``None``
        """
        for raw in batch:
            if not isinstance(raw, dict):
                continue
            record = EventRecord.from_dict(raw)
            if not _filter_matches(record=record, filter=self._filter):
                continue
            if len(self._buffer) >= self._buffer_limit:
                dropped = self._buffer.popleft()
                self._dropped_count = self._dropped_count + 1
                self._logger.warning(
                    "EventStream backpressure: dropped event id=%s type=%s",
                    getattr(dropped, "id", "?"),
                    getattr(dropped, "type", "?"),
                )
            self._buffer.append(record)
            rec_id = getattr(record, "id", None)
            if rec_id is not None:
                self._last_seen = rec_id
        return None


def _filter_matches(*, record: EventRecord, filter: EventFilter) -> bool:
    """
        Apply ``EventFilter`` to a single :class:`EventRecord`.

        :param record: The candidate record.
        :param filter: The active filter.

        :returns: ``True`` when the record passes all filter fields.
    """
    event_types = getattr(filter, "event_types", None)
    if event_types is not None and len(event_types) > 0:
        rec_type = getattr(record, "type", None)
        if rec_type not in event_types:
            return False

    severities = getattr(filter, "severities", None)
    if severities is not None and len(severities) > 0:
        rec_sev = getattr(record, "severity", None)
        if rec_sev not in severities:
            return False

    target_kind = getattr(filter, "target_kind", None)
    target_id = getattr(filter, "target_id", None)
    if target_kind is not None or target_id is not None:
        target = getattr(record, "target", None) or {}
        if target_kind is not None:
            if target.get("type") != target_kind:
                return False
        if target_id is not None:
            if target.get("id") != target_id:
                return False

    since = getattr(filter, "since", None)
    if since is not None:
        ts = getattr(record, "timestamp", None)
        if ts is not None and ts < since:
            return False

    return True
