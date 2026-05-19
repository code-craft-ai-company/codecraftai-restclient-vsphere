"""
    Tests for the vsphere-events-stream feature:
    - VSphereClient.Events surface
    - EventsGroup.stream yields EventRecord
    - Filter constrains the yielded set
    - Backpressure overflow increments drop counter
    - close halts polling
"""

import unittest

from typing import List
from unittest.mock import MagicMock

from automojo.credentials.basiccredential import BasicCredential

from automojo.interop.vsphere.apigroups.eventsgroup import EventsGroup
from automojo.interop.vsphere.apigroups.eventstream import EventStream
from automojo.interop.vsphere.model.event import EventRecord
from automojo.interop.vsphere.specs.eventfilter import EventFilter
from automojo.interop.vsphere.vsphereclient import VSphereClient


def _make_client() -> VSphereClient:
    cred = BasicCredential(
        identifier="vc", categories=["basic"], username="u", password="p",
    )
    client = VSphereClient(host="vc.example.com", credential=cred)
    client._session = MagicMock()
    client._auth_token = "tok"
    return client


def _ev(*, eid, etype, severity="INFO", target=None):
    rtnval = {"id": eid, "type": etype, "severity": severity}
    if target is not None:
        rtnval["target"] = target
    return rtnval


class TestStructural(unittest.TestCase):

    def test_events_property_surfaces_group(self) -> None:
        client = _make_client()
        events = client.Events
        self.assertIsInstance(events, EventsGroup)
        return


class TestStreamBasics(unittest.TestCase):

    def test_yields_event_records(self) -> None:
        client = _make_client()
        batches = [
            [_ev(eid="e1", etype="VmPoweredOn"), _ev(eid="e2", etype="VmPoweredOff")],
            [],
        ]

        def _fetcher(_last, _f):
            if len(batches) > 1:
                rtnval = batches.pop(0)
                return rtnval
            rtnval = batches[0]
            return rtnval

        stream = client.Events.stream(
            filter=EventFilter(), fetcher=_fetcher, sleeper=MagicMock(),
        )
        first = next(stream)
        second = next(stream)
        self.assertIsInstance(first, EventRecord)
        self.assertEqual(first.id, "e1")
        self.assertEqual(second.id, "e2")
        return

    def test_filter_event_types(self) -> None:
        client = _make_client()
        batch = [
            _ev(eid="e1", etype="VmPoweredOn"),
            _ev(eid="e2", etype="HostConnected"),
        ]
        calls = {"n": 0}

        def _fetcher(_last, _f):
            calls["n"] += 1
            if calls["n"] == 1:
                rtnval = batch
                return rtnval
            rtnval = []
            return rtnval

        stream = client.Events.stream(
            filter=EventFilter(event_types=["VmPoweredOn"]),
            fetcher=_fetcher, sleeper=MagicMock(),
        )
        first = next(stream)
        self.assertEqual(first.id, "e1")
        stream.close()
        return

    def test_filter_target(self) -> None:
        client = _make_client()
        batch = [
            _ev(eid="e1", etype="X", target={"type": "VM", "id": "vm-1"}),
            _ev(eid="e2", etype="X", target={"type": "VM", "id": "vm-2"}),
        ]
        rounds = {"n": 0}

        def _fetcher(_last, _f):
            rounds["n"] += 1
            if rounds["n"] == 1:
                rtnval = batch
                return rtnval
            rtnval = []
            return rtnval

        stream = client.Events.stream(
            filter=EventFilter(target_kind="VM", target_id="vm-2"),
            fetcher=_fetcher, sleeper=MagicMock(),
        )
        first = next(stream)
        self.assertEqual(first.id, "e2")
        stream.close()
        return

    def test_close_halts_polling(self) -> None:
        client = _make_client()

        def _fetcher(_last, _f):
            return []

        sleeper = MagicMock()
        stream = client.Events.stream(
            filter=EventFilter(), fetcher=_fetcher, sleeper=sleeper,
        )
        stream.close()
        with self.assertRaises(StopIteration):
            next(stream)
        return


class TestBackpressure(unittest.TestCase):

    def test_overflow_drops_oldest_and_increments_counter(self) -> None:
        client = _make_client()
        # Produce more events than the buffer limit, all in one batch.
        large_batch = [_ev(eid="e{}".format(i), etype="X") for i in range(5)]
        rounds = {"n": 0}

        def _fetcher(_last, _f):
            rounds["n"] += 1
            if rounds["n"] == 1:
                rtnval = large_batch
                return rtnval
            rtnval = []
            return rtnval

        stream = client.Events.stream(
            filter=EventFilter(), fetcher=_fetcher,
            sleeper=MagicMock(), buffer_limit=3,
        )
        # First call ingests the batch — buffer holds 3, 2 dropped.
        first = next(stream)
        self.assertEqual(stream.dropped_count, 2)
        # The dropped entries are the oldest; the survivors begin at e2.
        self.assertEqual(first.id, "e2")
        return


if __name__ == "__main__":
    unittest.main()
