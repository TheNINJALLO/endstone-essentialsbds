"""Main-thread scan orchestration for entity hotspot snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
from typing import Callable

from endstone_primebds.utils.config_util import load_config
from endstone_primebds.utils.entity_hotspots import (
    ActorSample,
    HotspotFilter,
    HotspotSettings,
    HotspotSnapshot,
    SnapshotSelection,
    SnapshotStore,
    build_rankings,
    sample_matches,
)


ActorReader = Callable[[object], ActorSample | None]
CompletionCallback = Callable[[HotspotSnapshot | None, str | None, int], None]


def load_hotspot_settings() -> HotspotSettings:
    config = load_config()
    modules = config.get("modules", {}) if isinstance(config, dict) else {}
    raw = modules.get("entity_hotspots", {}) if isinstance(modules, dict) else {}
    return HotspotSettings.from_mapping(raw)


@dataclass(slots=True)
class _ActiveScan:
    owner_key: str
    mode: str
    filters: HotspotFilter
    generation: int
    scan_id: str
    settings: HotspotSettings
    actor_reader: ActorReader
    callback: CompletionCallback
    started_at: float
    started_monotonic: float
    task: object | None = None
    actor_refs: list[object] | None = None
    samples: list[ActorSample] = field(default_factory=list)
    seen_ids: set[str] = field(default_factory=set)
    next_index: int = 0
    collection_ticks: int = 0
    actors_available: int = 0
    actors_examined: int = 0
    actors_skipped: int = 0
    duplicate_actors: int = 0
    acquisition_ms: float = 0.0

    def release_live_objects(self) -> None:
        self.actor_refs = None
        self.actor_reader = lambda _actor: None


class EntityHotspotScanService:
    """Collect live actors incrementally on the Endstone server thread.

    Endstone 0.11.9 exposes the level actor list as one indivisible operation. The
    service measures that acquisition, then validates and detaches at most the
    configured number of actor references per scheduler tick.
    """

    def __init__(
        self,
        plugin,
        settings_provider: Callable[[], HotspotSettings] = load_hotspot_settings,
        wall_clock: Callable[[], float] = time.time,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ):
        self._plugin = plugin
        self._settings_provider = settings_provider
        self._wall_clock = wall_clock
        self._monotonic_clock = monotonic_clock
        defaults = HotspotSettings()
        self.snapshots = SnapshotStore(
            defaults.max_retained_snapshots, defaults.snapshot_lifetime_seconds
        )
        self._active: dict[str, _ActiveScan] = {}
        self._generation: dict[str, int] = {}
        self._last_started: dict[str, float] = {}
        self._scan_sequence = 0
        self._stopped = False
        self._lock = threading.RLock()

    @staticmethod
    def sender_key(sender) -> str:
        unique_id = getattr(sender, "unique_id", None)
        if unique_id is not None:
            return f"player:{unique_id}"
        xuid = getattr(sender, "xuid", None)
        if xuid:
            return f"player-xuid:{xuid}"
        return f"sender:{type(sender).__name__}:{getattr(sender, 'name', 'unknown')}"

    def settings(self) -> HotspotSettings:
        settings = self._settings_provider()
        if not isinstance(settings, HotspotSettings):
            settings = HotspotSettings.from_mapping(settings)
        self.snapshots.reconfigure(
            settings.max_retained_snapshots, settings.snapshot_lifetime_seconds
        )
        return settings

    def current_time(self) -> float:
        return self._wall_clock()

    def start_scan(
        self,
        owner_key: str,
        mode: str,
        filters: HotspotFilter,
        actor_reader: ActorReader,
        callback: CompletionCallback,
    ) -> tuple[bool, str]:
        settings = self.settings()
        if not settings.enabled:
            return False, "Entity hotspot diagnostics are disabled in config.json."

        with self._lock:
            if self._stopped:
                return False, "Entity hotspot diagnostics are shutting down."

            now = self._monotonic_clock()
            remaining = settings.scan_cooldown_seconds - (
                now - self._last_started.get(owner_key, -1.0e30)
            )
            if remaining > 0:
                return False, f"Scan cooldown active; try again in {math_ceil(remaining)}s."

            previous = self._active.get(owner_key)
            if previous is None and len(self._active) >= settings.max_concurrent_scans:
                return False, "The hotspot scanner is busy; try again shortly."
            if previous is not None:
                self._cancel_state(previous)

            generation = self._generation.get(owner_key, 0) + 1
            self._generation[owner_key] = generation
            self._scan_sequence += 1
            scan_id = f"EH-{self._scan_sequence:04d}"
            state = _ActiveScan(
                owner_key=owner_key,
                mode=mode,
                filters=filters,
                generation=generation,
                scan_id=scan_id,
                settings=settings,
                actor_reader=actor_reader,
                callback=callback,
                started_at=self._wall_clock(),
                started_monotonic=now,
            )
            self._active[owner_key] = state
            self._last_started[owner_key] = now

            try:
                state.task = self._plugin.server.scheduler.run_task(
                    self._plugin,
                    lambda: self._tick(owner_key, generation),
                    delay=0,
                    period=1,
                )
            except Exception as exc:
                self._active.pop(owner_key, None)
                state.release_live_objects()
                return False, f"Could not schedule hotspot scan: {exc}"

        return True, f"Started loaded-entity scan {scan_id}. Results will appear when ready."

    def get_selected(self, owner_key: str) -> tuple[HotspotSnapshot, SnapshotSelection]:
        self.settings()
        return self.snapshots.get_selected(owner_key, self._wall_clock())

    def get_rank(self, owner_key: str, rank: int):
        self.settings()
        return self.snapshots.get_rank(owner_key, rank, self._wall_clock())

    def get_refresh_query(self, owner_key: str) -> tuple[HotspotSnapshot, SnapshotSelection]:
        self.settings()
        return self.snapshots.get_for_refresh(owner_key)

    def select_mode(self, owner_key: str, mode: str) -> HotspotSnapshot:
        self.settings()
        return self.snapshots.select_mode(owner_key, mode, self._wall_clock())

    def abandon(self, owner_key: str) -> None:
        with self._lock:
            state = self._active.pop(owner_key, None)
            if state is not None:
                self._generation[owner_key] = state.generation + 1
                self._cancel_state(state)
            self._last_started.pop(owner_key, None)
        self.snapshots.remove_owner(owner_key)

    def shutdown(self) -> None:
        with self._lock:
            self._stopped = True
            for state in list(self._active.values()):
                self._cancel_state(state)
            self._active.clear()
            self._generation.clear()
            self._last_started.clear()
        self.snapshots.clear()

    def _tick(self, owner_key: str, generation: int) -> None:
        with self._lock:
            state = self._active.get(owner_key)
            if (
                state is None
                or state.generation != generation
                or self._stopped
            ):
                return

        if state.actor_refs is None:
            acquisition_started = self._monotonic_clock()
            try:
                # Endstone 0.11.9 returns all currently exposed loaded actors in
                # one call; there is no incremental acquisition API in this version.
                state.actor_refs = list(self._plugin.server.level.actors)
                state.actors_available = len(state.actor_refs)
            except Exception as exc:
                self._fail(state, f"Could not acquire loaded actors: {exc}")
                return
            state.acquisition_ms = (
                self._monotonic_clock() - acquisition_started
            ) * 1000.0

        state.collection_ticks += 1
        processed_this_tick = 0
        limit_reason = ""

        while state.next_index < state.actors_available:
            if processed_this_tick >= state.settings.actors_per_tick:
                break
            if state.actors_examined >= state.settings.max_actors:
                limit_reason = f"maximum actor limit ({state.settings.max_actors})"
                break
            if (
                self._monotonic_clock() - state.started_monotonic
                >= state.settings.max_scan_seconds
            ):
                limit_reason = f"scan time limit ({state.settings.max_scan_seconds:g}s)"
                break

            actor = state.actor_refs[state.next_index]
            state.next_index += 1
            state.actors_examined += 1
            processed_this_tick += 1
            try:
                sample = state.actor_reader(actor)
            except Exception:
                state.actors_skipped += 1
                continue
            if sample is None:
                state.actors_skipped += 1
                continue
            if sample.stable_id in state.seen_ids:
                state.duplicate_actors += 1
                continue
            state.seen_ids.add(sample.stable_id)
            if sample_matches(sample, state.filters, state.settings.include_players):
                state.samples.append(sample)

        if limit_reason:
            self._finish(state, complete=False, limit_reason=limit_reason)
            return
        if state.next_index >= state.actors_available:
            if state.actors_skipped:
                reason = f"{state.actors_skipped} actor(s) inaccessible, invalid, or changed"
                self._finish(state, complete=False, limit_reason=reason)
            else:
                self._finish(state, complete=True, limit_reason="")

    def _finish(self, state: _ActiveScan, complete: bool, limit_reason: str) -> None:
        samples = tuple(state.samples)
        state.samples.clear()
        state.release_live_objects()
        chunks, groups = build_rankings(samples, state.settings.dense_chunk_threshold)
        completed_at = self._wall_clock()
        duration_ms = (self._monotonic_clock() - state.started_monotonic) * 1000.0
        snapshot = HotspotSnapshot(
            scan_id=state.scan_id,
            owner_key=state.owner_key,
            filters=state.filters,
            started_at=state.started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            acquisition_ms=state.acquisition_ms,
            collection_ticks=state.collection_ticks,
            actors_available=state.actors_available,
            actors_examined=state.actors_examined,
            actors_matched=len(samples),
            actors_skipped=state.actors_skipped,
            duplicate_actors=state.duplicate_actors,
            complete=complete,
            limit_reason=limit_reason,
            chunks=chunks,
            groups=groups,
        )

        with self._lock:
            current = self._active.get(state.owner_key)
            if current is not state or self._stopped:
                self._cancel_state(state)
                return
            self._active.pop(state.owner_key, None)
            self._cancel_task(state)
            self.snapshots.put(snapshot, state.mode)
            callback = state.callback
            state.callback = lambda _snapshot, _error, _page: None

        try:
            callback(snapshot, None, 1)
        except Exception:
            # A player may disconnect between scan ticks. No live object is retained.
            pass

    def _fail(self, state: _ActiveScan, message: str) -> None:
        state.samples.clear()
        state.release_live_objects()
        with self._lock:
            if self._active.get(state.owner_key) is state:
                self._active.pop(state.owner_key, None)
            self._cancel_task(state)
            callback = state.callback
            state.callback = lambda _snapshot, _error, _page: None
        try:
            callback(None, message, 1)
        except Exception:
            pass

    def _cancel_task(self, state: _ActiveScan) -> None:
        task = state.task
        state.task = None
        if task is not None:
            try:
                task.cancel()
            except Exception:
                try:
                    self._plugin.server.scheduler.cancel_task(task.task_id)
                except Exception:
                    pass

    def _cancel_state(self, state: _ActiveScan) -> None:
        self._cancel_task(state)
        state.samples.clear()
        state.seen_ids.clear()
        state.release_live_objects()
        state.callback = lambda _snapshot, _error, _page: None


def math_ceil(value: float) -> int:
    # Local helper keeps math import out of the scan's hot path.
    integer = int(value)
    return integer if value == integer else integer + 1
