from __future__ import annotations

from dataclasses import replace
import sys
import types

from conftest import SRC_PACKAGE, load_source
from endstone_primebds.utils.entity_hotspots import (
    ActorSample,
    HotspotFilter,
    HotspotSettings,
)


config_stub = types.ModuleType("endstone_primebds.utils.config_util")
config_stub.load_config = lambda: {"modules": {"entity_hotspots": {}}}
sys.modules["endstone_primebds.utils.config_util"] = config_stub
service_module = load_source(
    "endstone_primebds.utils.entity_hotspot_service",
    SRC_PACKAGE / "utils" / "entity_hotspot_service.py",
)
EntityHotspotScanService = service_module.EntityHotspotScanService


class Clock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def wall(self):
        return 1_000.0 + self.value

    def advance(self, seconds):
        self.value += seconds


class Task:
    def __init__(self, callback, task_id):
        self.callback = callback
        self.task_id = task_id
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True


class Scheduler:
    def __init__(self):
        self.tasks = []

    def run_task(self, _plugin, callback, delay=0, period=0):
        task = Task(callback, len(self.tasks) + 1)
        self.tasks.append(task)
        return task

    def tick(self):
        for task in list(self.tasks):
            if not task.is_cancelled:
                task.callback()


class Level:
    def __init__(self, actors):
        self.actors = actors


class Server:
    def __init__(self, actors):
        self.scheduler = Scheduler()
        self.level = Level(actors)


class Plugin:
    def __init__(self, actors):
        self.server = Server(actors)


def sample(stable_id: str, x: float = 1.0):
    return ActorSample(
        stable_id,
        "minecraft:chicken",
        "mob",
        "overworld",
        "Overworld",
        x,
        64,
        1,
    )


def make_service(actors, **changes):
    clock = Clock()
    settings = replace(
        HotspotSettings(),
        scan_cooldown_seconds=0,
        actors_per_tick=1,
        dense_chunk_threshold=1,
        **changes,
    )
    plugin = Plugin(actors)
    service = EntityHotspotScanService(
        plugin,
        settings_provider=lambda: settings,
        wall_clock=clock.wall,
        monotonic_clock=clock.monotonic,
    )
    return service, plugin, clock


def run_until_idle(plugin, maximum_ticks=20):
    for _ in range(maximum_ticks):
        plugin.server.scheduler.tick()
        if all(task.is_cancelled for task in plugin.server.scheduler.tasks):
            return
    raise AssertionError("scan did not finish")


def test_incremental_scan_builds_snapshot_and_ignores_duplicate_ids():
    service, plugin, _clock = make_service(
        [sample("same", 1), sample("same", 2), sample("other", 17)]
    )
    completed = []

    started, _message = service.start_scan(
        "admin",
        "chunks",
        HotspotFilter.create(),
        lambda value: value,
        lambda snapshot, error, page: completed.append((snapshot, error, page)),
    )
    assert started is True
    run_until_idle(plugin)

    snapshot_result = completed[0][0]
    assert snapshot_result.collection_ticks == 3
    assert snapshot_result.actors_examined == 3
    assert snapshot_result.actors_matched == 2
    assert snapshot_result.duplicate_actors == 1
    assert snapshot_result.complete is True


def test_despawned_and_inaccessible_actors_mark_scan_incomplete():
    service, plugin, _clock = make_service([sample("ok"), None, "bad"])
    completed = []

    def reader(value):
        if value == "bad":
            raise RuntimeError("despawned")
        return value

    service.start_scan(
        "admin",
        "chunks",
        HotspotFilter.create(),
        reader,
        lambda snapshot, error, page: completed.append(snapshot),
    )
    run_until_idle(plugin)

    result = completed[0]
    assert result.complete is False
    assert result.actors_skipped == 2
    assert "inaccessible" in result.limit_reason


def test_actor_limit_is_reported_as_incomplete():
    service, plugin, _clock = make_service(
        [sample("1"), sample("2"), sample("3")], max_actors=2
    )
    completed = []
    service.start_scan(
        "admin",
        "chunks",
        HotspotFilter.create(),
        lambda value: value,
        lambda snapshot, error, page: completed.append(snapshot),
    )
    run_until_idle(plugin)

    assert completed[0].complete is False
    assert completed[0].actors_examined == 2
    assert "maximum actor limit" in completed[0].limit_reason


def test_scan_duration_limit_is_reported_as_incomplete():
    service, plugin, clock = make_service(
        [sample("1"), sample("2")], max_scan_seconds=0.25
    )
    completed = []

    def slow_reader(value):
        clock.advance(0.3)
        return value

    service.start_scan(
        "admin",
        "chunks",
        HotspotFilter.create(),
        slow_reader,
        lambda snapshot, error, page: completed.append(snapshot),
    )
    run_until_idle(plugin)

    assert completed[0].complete is False
    assert completed[0].actors_examined == 1
    assert "scan time limit" in completed[0].limit_reason


def test_newer_same_sender_scan_prevents_stale_callback_and_selection():
    service, plugin, _clock = make_service([sample("one")])
    old_callbacks = []
    new_callbacks = []
    service.start_scan(
        "admin",
        "chunks",
        HotspotFilter.create(),
        lambda value: value,
        lambda snapshot, error, page: old_callbacks.append(snapshot),
    )
    service.start_scan(
        "admin",
        "groups",
        HotspotFilter.create(),
        lambda value: value,
        lambda snapshot, error, page: new_callbacks.append(snapshot),
    )
    run_until_idle(plugin)

    assert old_callbacks == []
    assert new_callbacks[0].scan_id == "EH-0002"
    assert service.get_selected("admin")[1].mode == "groups"


def test_concurrency_is_bounded_across_senders():
    service, _plugin, _clock = make_service([sample("one")], max_concurrent_scans=1)
    first, _ = service.start_scan(
        "admin-a",
        "chunks",
        HotspotFilter.create(),
        lambda value: value,
        lambda snapshot, error, page: None,
    )
    second, message = service.start_scan(
        "admin-b",
        "chunks",
        HotspotFilter.create(),
        lambda value: value,
        lambda snapshot, error, page: None,
    )

    assert first is True
    assert second is False
    assert "busy" in message


def test_disconnect_and_plugin_disable_cancel_tasks_and_release_results():
    service, plugin, _clock = make_service([sample("one"), sample("two")])
    service.start_scan(
        "admin",
        "chunks",
        HotspotFilter.create(),
        lambda value: value,
        lambda snapshot, error, page: None,
    )
    service.abandon("admin")
    assert all(task.is_cancelled for task in plugin.server.scheduler.tasks)
    service.shutdown()
    assert service.start_scan(
        "admin",
        "chunks",
        HotspotFilter.create(),
        lambda value: value,
        lambda snapshot, error, page: None,
    )[0] is False
