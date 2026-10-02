"""Tests for the event sourcing system."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.event_sourcing import (
    ConcurrencyError,
    EventReplayer,
    EventStore,
    EventVersion,
    ProjectionBuilder,
    Snapshot,
    SnapshotManager,
    VersionedEvent,
    VersionMigrator,
)


class TestEventStore(unittest.TestCase):
    def setUp(self) -> None:
        self.store = EventStore()

    def test_append_and_get_stream(self) -> None:
        self.store.append("s1", "UserCreated", {"name": "Alice"})
        self.store.append("s1", "UserUpdated", {"name": "Bob"})
        events = self.store.get_stream("s1")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_type, "UserCreated")
        self.assertEqual(events[1].event_type, "UserUpdated")
        self.assertEqual(events[0].version, 1)
        self.assertEqual(events[1].version, 2)

    def test_append_with_expected_version_success(self) -> None:
        self.store.append("s1", "E1", {})
        event = self.store.append("s1", "E2", {}, expected_version=1)
        self.assertEqual(event.version, 2)

    def test_append_with_expected_version_conflict(self) -> None:
        self.store.append("s1", "E1", {})
        with self.assertRaises(ConcurrencyError):
            self.store.append("s1", "E2", {}, expected_version=0)

    def test_get_stream_after_version(self) -> None:
        for i in range(5):
            self.store.append("s1", f"Event{i}", {"i": i})
        events = self.store.get_stream("s1", after_version=2)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].version, 3)

    def test_get_all_with_filters(self) -> None:
        self.store.append("s1", "TypeA", {"x": 1})
        self.store.append("s2", "TypeB", {"x": 2})
        self.store.append("s3", "TypeA", {"x": 3})

        all_events = self.store.get_all()
        self.assertEqual(len(all_events), 3)

        type_a = self.store.get_all(event_type="TypeA")
        self.assertEqual(len(type_a), 2)

    def test_get_current_version(self) -> None:
        self.assertEqual(self.store.get_current_version("s1"), 0)
        self.store.append("s1", "E1", {})
        self.assertEqual(self.store.get_current_version("s1"), 1)
        self.store.append("s1", "E2", {})
        self.assertEqual(self.store.get_current_version("s1"), 2)

    def test_subscribe(self) -> None:
        received: list = []
        self.store.subscribe(lambda e: received.append(e))
        self.store.append("s1", "E1", {})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].event_type, "E1")

    def test_unsubscribe(self) -> None:
        received: list = []
        cb = lambda e: received.append(e)
        self.store.subscribe(cb)
        self.store.unsubscribe(cb)
        self.store.append("s1", "E1", {})
        self.assertEqual(len(received), 0)

    def test_metadata(self) -> None:
        meta = {"correlation_id": "abc-123"}
        event = self.store.append("s1", "E1", {}, metadata=meta)
        self.assertEqual(event.metadata["correlation_id"], "abc-123")

    def test_to_dict_from_dict_roundtrip(self) -> None:
        event = self.store.append("s1", "E1", {"key": "val"})
        d = event.to_dict()
        restored = type(event).from_dict(d)
        self.assertEqual(restored.event_id, event.event_id)
        self.assertEqual(restored.payload, event.payload)


class TestEventReplayer(unittest.TestCase):
    def setUp(self) -> None:
        self.store = EventStore()
        self.replayer = EventReplayer(self.store)

    def test_replay_stream(self) -> None:
        self.store.append("s1", "Add", {"amount": 10})
        self.store.append("s1", "Add", {"amount": 20})
        self.store.append("s1", "Subtract", {"amount": 5})

        def reducer(state: dict, event) -> dict:
            if event.event_type == "Add":
                state["total"] += event.payload["amount"]
            elif event.event_type == "Subtract":
                state["total"] -= event.payload["amount"]
            return state

        result = self.replayer.replay_stream("s1", reducer, {"total": 0})
        self.assertEqual(result.state["total"], 25)
        self.assertEqual(result.events_replayed, 3)
        self.assertEqual(result.last_version, 3)
        self.assertGreaterEqual(result.duration_ms, 0)

    def test_replay_all(self) -> None:
        self.store.append("s1", "Add", {"amount": 10})
        self.store.append("s2", "Add", {"amount": 20})

        def reducer(state: dict, event) -> dict:
            if event.event_type == "Add":
                state["total"] += event.payload["amount"]
            return state

        result = self.replayer.replay_all(reducer, {"total": 0})
        self.assertEqual(result.state["total"], 30)
        self.assertEqual(result.events_replayed, 2)

    def test_replay_filtered(self) -> None:
        self.store.append("s1", "Add", {"amount": 10})
        self.store.append("s2", "Add", {"amount": 20})
        self.store.append("s3", "Add", {"amount": 30})

        def reducer(state: dict, event) -> dict:
            state["total"] += event.payload["amount"]
            return state

        result = self.replayer.replay_filtered(
            ["s1", "s3"], reducer, {"total": 0}
        )
        self.assertEqual(result.state["total"], 40)

    def test_replay_with_predicate(self) -> None:
        self.store.append("s1", "Add", {"amount": 10})
        self.store.append("s1", "Special", {"amount": 100})
        self.store.append("s1", "Add", {"amount": 20})

        def reducer(state: dict, event) -> dict:
            state["total"] += event.payload["amount"]
            return state

        result = self.replayer.replay_filtered(
            ["s1"], reducer, {"total": 0},
            predicate=lambda e: e.event_type == "Add",
        )
        self.assertEqual(result.state["total"], 30)

    def test_replay_empty_stream(self) -> None:
        result = self.replayer.replay_stream(
            "empty", lambda s, e: s, {"total": 0}
        )
        self.assertEqual(result.state["total"], 0)
        self.assertEqual(result.events_replayed, 0)


class TestSnapshotManager(unittest.TestCase):
    def setUp(self) -> None:
        self.store = EventStore()
        self.snapshots = SnapshotManager(self.store)

    def test_save_and_get_latest(self) -> None:
        snap = self.snapshots.save_snapshot("s1", {"count": 42}, version=5)
        self.assertEqual(snap.stream_id, "s1")
        self.assertEqual(snap.state["count"], 42)
        self.assertEqual(snap.version, 5)

        latest = self.snapshots.get_latest("s1")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.state["count"], 42)

    def test_save_auto_version(self) -> None:
        self.store.append("s1", "E1", {})
        self.store.append("s1", "E2", {})
        snap = self.snapshots.save_snapshot("s1", {"val": 1})
        self.assertEqual(snap.version, 2)

    def test_get_at_version(self) -> None:
        self.snapshots.save_snapshot("s1", {"v": 1}, version=1)
        self.snapshots.save_snapshot("s1", {"v": 3}, version=3)
        self.snapshots.save_snapshot("s1", {"v": 5}, version=5)

        snap = self.snapshots.get_at_version("s1", 4)
        self.assertIsNotNone(snap)
        self.assertEqual(snap.version, 3)
        self.assertEqual(snap.state["v"], 3)

    def test_get_all_for_stream(self) -> None:
        self.snapshots.save_snapshot("s1", {"v": 1}, version=1)
        self.snapshots.save_snapshot("s1", {"v": 2}, version=2)
        snaps = self.snapshots.get_all_for_stream("s1")
        self.assertEqual(len(snaps), 2)
        self.assertEqual(snaps[0].version, 2)

    def test_delete_stream_snapshots(self) -> None:
        self.snapshots.save_snapshot("s1", {"v": 1}, version=1)
        self.snapshots.save_snapshot("s1", {"v": 2}, version=2)
        deleted = self.snapshots.delete_stream_snapshots("s1")
        self.assertEqual(deleted, 2)
        self.assertIsNone(self.snapshots.get_latest("s1"))

    def test_should_snapshot(self) -> None:
        self.assertFalse(self.snapshots.should_snapshot("s1", 3))
        for i in range(3):
            self.store.append("s1", f"E{i}", {})
        self.assertTrue(self.snapshots.should_snapshot("s1", 3))

    def test_should_snapshot_with_existing(self) -> None:
        for i in range(5):
            self.store.append("s1", f"E{i}", {})
        self.snapshots.save_snapshot("s1", {}, version=2)
        self.assertTrue(self.snapshots.should_snapshot("s1", 3))
        self.assertFalse(self.snapshots.should_snapshot("s1", 5))

    def test_get_latest_empty(self) -> None:
        self.assertIsNone(self.snapshots.get_latest("nonexistent"))


class TestProjectionBuilder(unittest.TestCase):
    def setUp(self) -> None:
        self.store = EventStore()
        self.builder = ProjectionBuilder(self.store)

    def test_register_and_build(self) -> None:
        self.builder.register(
            "counter",
            {"count": 0},
            {"Increment": lambda s, e: {**s, "count": s["count"] + 1}},
        )
        proj = self.builder.build("counter")
        self.assertEqual(proj.name, "counter")
        self.assertEqual(proj.state["count"], 0)

    def test_rebuild(self) -> None:
        self.store.append("s1", "Increment", {})
        self.store.append("s1", "Increment", {})
        self.store.append("s1", "Increment", {})

        self.builder.register(
            "counter",
            {"count": 0},
            {"Increment": lambda s, e: {**s, "count": s["count"] + 1}},
        )
        proj = self.builder.rebuild("counter")
        self.assertEqual(proj.state["count"], 3)
        self.assertEqual(proj.event_count, 3)

    def test_rebuild_all(self) -> None:
        self.store.append("s1", "Increment", {})
        self.store.append("s2", "Decrement", {})

        self.builder.register(
            "counter",
            {"count": 0},
            {
                "Increment": lambda s, e: {**s, "count": s["count"] + 1},
                "Decrement": lambda s, e: {**s, "count": s["count"] - 1},
            },
        )
        self.builder.register(
            "log",
            {"events": []},
            {
                "Increment": lambda s, e: {**s, "events": s["events"] + ["inc"]},
                "Decrement": lambda s, e: {**s, "events": s["events"] + ["dec"]},
            },
        )
        results = self.builder.rebuild_all()
        self.assertEqual(results["counter"].state["count"], 0)
        self.assertEqual(results["log"].state["events"], ["inc", "dec"])

    def test_update_from_events(self) -> None:
        self.store.append("s1", "Increment", {})
        self.builder.register(
            "counter",
            {"count": 0},
            {"Increment": lambda s, e: {**s, "count": s["count"] + 1}},
        )
        proj = self.builder.update_from_events("counter")
        self.assertEqual(proj.state["count"], 1)

        self.store.append("s1", "Increment", {})
        proj = self.builder.update_from_events("counter")
        self.assertEqual(proj.state["count"], 2)

    def test_update_all_from_events(self) -> None:
        self.store.append("s1", "Increment", {})
        self.builder.register(
            "counter",
            {"count": 0},
            {"Increment": lambda s, e: {**s, "count": s["count"] + 1}},
        )
        results = self.builder.update_all_from_events()
        self.assertEqual(results["counter"].state["count"], 1)

    def test_list_projections(self) -> None:
        self.builder.register("a", {}, {})
        self.builder.register("b", {}, {})
        names = self.builder.list_projections_names()
        self.assertIn("a", names)
        self.assertIn("b", names)

    def test_get_all_states(self) -> None:
        self.store.append("s1", "Increment", {})
        self.builder.register(
            "counter",
            {"count": 0},
            {"Increment": lambda s, e: {**s, "count": s["count"] + 1}},
        )
        self.builder.rebuild("counter")
        states = self.builder.get_all_states()
        self.assertIn("counter", states)
        self.assertEqual(states["counter"].state["count"], 1)

    def test_unknown_projection_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.builder.build("nonexistent")

    def test_projection_reset(self) -> None:
        self.store.append("s1", "Increment", {})
        self.builder.register(
            "counter",
            {"count": 0},
            {"Increment": lambda s, e: {**s, "count": s["count"] + 1}},
        )
        proj = self.builder.rebuild("counter")
        self.assertEqual(proj.event_count, 1)
        proj.reset()
        self.assertEqual(proj.event_count, 0)
        self.assertEqual(proj.last_processed_seq, 0)


class TestVersionMigrator(unittest.TestCase):
    def setUp(self) -> None:
        self.migrator = VersionMigrator()

    def test_register_and_migrate(self) -> None:
        self.migrator.register(
            "UserCreated",
            1,
            lambda p: {**p, "full_name": f"{p['first_name']} {p['last_name']}"},
        )
        result = self.migrator.migrate(
            "UserCreated",
            {"first_name": "Alice", "last_name": "Smith"},
            from_version=1,
            to_version=2,
        )
        self.assertEqual(result.version, 2)
        self.assertTrue(result.migrated)
        self.assertEqual(result.payload["full_name"], "Alice Smith")

    def test_migrate_same_version(self) -> None:
        result = self.migrator.migrate("E", {"x": 1}, from_version=1, to_version=1)
        self.assertEqual(result.version, 1)
        self.assertFalse(result.migrated)
        self.assertEqual(result.payload, {"x": 1})

    def test_migrate_downgrade_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.migrator.migrate("E", {}, from_version=2, to_version=1)

    def test_migrate_no_path_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.migrator.migrate("Unknown", {}, from_version=1, to_version=2)

    def test_chained_migration(self) -> None:
        self.migrator.register("E", 1, lambda p: {**p, "v": 2})
        self.migrator.register("E", 2, lambda p: {**p, "v": 3})
        result = self.migrator.migrate("E", {"v": 1}, from_version=1, to_version=3)
        self.assertEqual(result.payload["v"], 3)
        self.assertTrue(result.migrated)

    def test_can_migrate(self) -> None:
        self.migrator.register("E", 1, lambda p: p)
        self.assertTrue(self.migrator.can_migrate("E", 1, 2))
        self.assertTrue(self.migrator.can_migrate("E", 1, 1))
        self.assertFalse(self.migrator.can_migrate("E", 1, 3))
        self.assertFalse(self.migrator.can_migrate("E", 2, 1))

    def test_get_registered_types(self) -> None:
        self.migrator.register("A", 1, lambda p: p)
        self.migrator.register("B", 1, lambda p: p)
        types = self.migrator.get_registered_types()
        self.assertIn("A", types)
        self.assertIn("B", types)

    def test_get_migration_path(self) -> None:
        path = self.migrator.get_migration_path("E", 1, 4)
        self.assertEqual(path, [1, 2, 3, 4])

    def test_versioned_event_roundtrip(self) -> None:
        ve = VersionedEvent(event_type="Test", version=2, payload={"a": 1}, migrated=True)
        d = ve.to_dict()
        restored = VersionedEvent.from_dict(d)
        self.assertEqual(restored.event_type, "Test")
        self.assertEqual(restored.version, 2)
        self.assertEqual(restored.payload, {"a": 1})
        self.assertTrue(restored.migrated)


class TestIntegration(unittest.TestCase):
    """Integration tests combining all components."""

    def test_full_event_sourcing_flow(self) -> None:
        store = EventStore()
        snapshots = SnapshotManager(store)
        builder = ProjectionBuilder(store, snapshots)
        migrator = VersionMigrator()

        # Register projection
        builder.register(
            "account_balance",
            {"balance": 0, "tx_count": 0},
            {
                "Deposit": lambda s, e: {
                    **s,
                    "balance": s["balance"] + e.payload["amount"],
                    "tx_count": s["tx_count"] + 1,
                },
                "Withdrawal": lambda s, e: {
                    **s,
                    "balance": s["balance"] - e.payload["amount"],
                    "tx_count": s["tx_count"] + 1,
                },
            },
        )

        # Append events
        store.append("acct-1", "Deposit", {"amount": 100})
        store.append("acct-1", "Deposit", {"amount": 50})
        store.append("acct-1", "Withdrawal", {"amount": 30})

        # Rebuild projection
        proj = builder.rebuild("account_balance")
        self.assertEqual(proj.state["balance"], 120)
        self.assertEqual(proj.state["tx_count"], 3)

        # Save snapshot
        snap = snapshots.save_snapshot("acct-1", proj.state)
        self.assertEqual(snap.state["balance"], 120)

        # Add more events and update incrementally
        store.append("acct-1", "Deposit", {"amount": 200})
        proj = builder.update_from_events("account_balance")
        self.assertEqual(proj.state["balance"], 320)
        self.assertEqual(proj.state["tx_count"], 4)

        # Replay from snapshot
        replayer = EventReplayer(store)
        latest_snap = snapshots.get_latest("acct-1")
        self.assertIsNotNone(latest_snap)

        def reducer(state: dict, event) -> dict:
            if event.event_type == "Deposit":
                state["balance"] += event.payload["amount"]
            elif event.event_type == "Withdrawal":
                state["balance"] -= event.payload["amount"]
            return state

        result = replayer.replay_stream(
            "acct-1", reducer, latest_snap.state, after_version=latest_snap.version
        )
        self.assertEqual(result.state["balance"], 320)

    def test_concurrent_append_conflict(self) -> None:
        store = EventStore()
        store.append("s1", "E1", {})
        with self.assertRaises(ConcurrencyError):
            store.append("s1", "E2", {}, expected_version=0)
        # Correct version should work
        event = store.append("s1", "E2", {}, expected_version=1)
        self.assertEqual(event.version, 2)


if __name__ == "__main__":
    unittest.main()
