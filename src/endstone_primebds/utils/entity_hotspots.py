"""Pure-data helpers for loaded-entity hotspot diagnostics.

This module deliberately has no Endstone imports. Live server objects are sampled by
``EntityHotspotScanService`` and discarded before these aggregation helpers run.
"""

from __future__ import annotations

from collections import Counter, OrderedDict, deque
from dataclasses import dataclass
import math
import threading
from typing import Iterable, Mapping, Sequence


FILTER_CATEGORIES = frozenset({"all", "mobs", "items", "other"})
RANKING_MODES = frozenset({"chunks", "groups"})


def chunk_coordinates(x: float, z: float) -> tuple[int, int]:
    """Return floor-based Bedrock chunk coordinates, including for negatives."""

    return math.floor(x / 16.0), math.floor(z / 16.0)


def canonical_dimension(value: str) -> str:
    """Normalize common dimension aliases while preserving custom names."""

    normalized = str(value).strip().lower()
    aliases = {
        "0": "overworld",
        "minecraft:overworld": "overworld",
        "overworld": "overworld",
        "1": "nether",
        "minecraft:nether": "nether",
        "minecraft:the_nether": "nether",
        "the_nether": "nether",
        "nether": "nether",
        "2": "the_end",
        "minecraft:the_end": "the_end",
        "the end": "the_end",
        "theend": "the_end",
        "end": "the_end",
        "the_end": "the_end",
    }
    return aliases.get(normalized, normalized)


def validate_entity_filter(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in FILTER_CATEGORIES:
        return normalized
    if ":" in normalized and not any(character.isspace() for character in normalized):
        namespace, identifier = normalized.split(":", 1)
        if namespace and identifier:
            return normalized
    raise ValueError(
        "entity filter must be all, mobs, items, other, or a full namespaced identifier"
    )


@dataclass(frozen=True, slots=True)
class HotspotFilter:
    dimension: str = "all"
    entity: str = "all"

    @classmethod
    def create(cls, dimension: str = "all", entity: str = "all") -> "HotspotFilter":
        normalized_dimension = canonical_dimension(dimension)
        if not normalized_dimension or any(
            character.isspace() for character in normalized_dimension
        ):
            raise ValueError("dimension must be all or one dimension name")
        return cls(normalized_dimension, validate_entity_filter(entity))


@dataclass(frozen=True, slots=True)
class HotspotSettings:
    enabled: bool = True
    write_report_file: bool = True
    results_per_page: int = 5
    include_players: bool = False
    scan_cooldown_seconds: float = 15.0
    snapshot_lifetime_seconds: float = 300.0
    max_retained_snapshots: int = 16
    max_concurrent_scans: int = 1
    max_actors: int = 20_000
    max_scan_seconds: float = 8.0
    actors_per_tick: int = 750
    dense_chunk_threshold: int = 10
    teleport_enabled: bool = True
    teleport_horizontal_radius: int = 4
    teleport_vertical_radius: int = 32
    teleport_max_candidates: int = 512

    @classmethod
    def from_mapping(cls, raw: Mapping | None) -> "HotspotSettings":
        values = raw if isinstance(raw, Mapping) else {}
        defaults = cls()

        def integer(name: str, default: int, minimum: int, maximum: int) -> int:
            try:
                return max(minimum, min(maximum, int(values.get(name, default))))
            except (TypeError, ValueError):
                return default

        def number(name: str, default: float, minimum: float, maximum: float) -> float:
            try:
                return max(minimum, min(maximum, float(values.get(name, default))))
            except (TypeError, ValueError):
                return default

        def boolean(name: str, default: bool) -> bool:
            value = values.get(name, default)
            return value if isinstance(value, bool) else default

        return cls(
            enabled=boolean("enabled", defaults.enabled),
            write_report_file=boolean(
                "write_report_file", defaults.write_report_file
            ),
            results_per_page=integer("results_per_page", defaults.results_per_page, 1, 10),
            include_players=boolean("include_players", defaults.include_players),
            scan_cooldown_seconds=number(
                "scan_cooldown_seconds", defaults.scan_cooldown_seconds, 0.0, 3_600.0
            ),
            snapshot_lifetime_seconds=number(
                "snapshot_lifetime_seconds", defaults.snapshot_lifetime_seconds, 10.0, 86_400.0
            ),
            max_retained_snapshots=integer(
                "max_retained_snapshots", defaults.max_retained_snapshots, 1, 128
            ),
            max_concurrent_scans=integer(
                "max_concurrent_scans", defaults.max_concurrent_scans, 1, 4
            ),
            max_actors=integer("max_actors", defaults.max_actors, 100, 250_000),
            max_scan_seconds=number(
                "max_scan_seconds", defaults.max_scan_seconds, 0.25, 60.0
            ),
            actors_per_tick=integer(
                "actors_per_tick", defaults.actors_per_tick, 25, 10_000
            ),
            dense_chunk_threshold=integer(
                "dense_chunk_threshold", defaults.dense_chunk_threshold, 1, 100_000
            ),
            teleport_enabled=boolean("teleport_enabled", defaults.teleport_enabled),
            teleport_horizontal_radius=integer(
                "teleport_horizontal_radius",
                defaults.teleport_horizontal_radius,
                0,
                12,
            ),
            teleport_vertical_radius=integer(
                "teleport_vertical_radius", defaults.teleport_vertical_radius, 2, 384
            ),
            teleport_max_candidates=integer(
                "teleport_max_candidates", defaults.teleport_max_candidates, 16, 4_096
            ),
        )


@dataclass(frozen=True, slots=True)
class ActorSample:
    stable_id: str
    type_id: str
    category: str
    dimension_key: str
    dimension_name: str
    x: float
    y: float
    z: float
    item_quantity: int = 0


@dataclass(frozen=True, slots=True)
class ChunkHotspot:
    dimension_key: str
    dimension_name: str
    chunk_x: int
    chunk_z: int
    total: int
    mob_count: int
    item_entity_count: int
    player_count: int
    other_count: int
    item_quantity: int
    min_y: float
    max_y: float
    busiest_section_y: int
    busiest_section_count: int
    representative_x: float
    representative_y: float
    representative_z: float
    type_counts: tuple[tuple[str, int], ...]
    category_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class GroupHotspot:
    dimension_key: str
    dimension_name: str
    total: int
    chunk_count: int
    min_chunk_x: int
    max_chunk_x: int
    min_chunk_z: int
    max_chunk_z: int
    min_y: float
    max_y: float
    average_per_chunk: float
    peak_chunk_x: int
    peak_chunk_z: int
    peak_chunk_count: int
    representative_x: float
    representative_y: float
    representative_z: float
    mob_count: int
    item_entity_count: int
    player_count: int
    other_count: int
    item_quantity: int
    type_counts: tuple[tuple[str, int], ...]
    category_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class HotspotSnapshot:
    scan_id: str
    owner_key: str
    filters: HotspotFilter
    started_at: float
    completed_at: float
    duration_ms: float
    acquisition_ms: float
    collection_ticks: int
    actors_available: int
    actors_examined: int
    actors_matched: int
    actors_skipped: int
    duplicate_actors: int
    complete: bool
    limit_reason: str
    chunks: tuple[ChunkHotspot, ...]
    groups: tuple[GroupHotspot, ...]

    def results(self, mode: str) -> tuple[ChunkHotspot, ...] | tuple[GroupHotspot, ...]:
        if mode == "chunks":
            return self.chunks
        if mode == "groups":
            return self.groups
        raise ValueError(f"unknown ranking mode: {mode}")


@dataclass(frozen=True, slots=True)
class SnapshotSelection:
    snapshot_id: str
    mode: str


def sample_matches(sample: ActorSample, filters: HotspotFilter, include_players: bool) -> bool:
    if sample.category == "player" and not include_players:
        return False
    if filters.dimension != "all" and canonical_dimension(sample.dimension_key) != filters.dimension:
        if canonical_dimension(sample.dimension_name) != filters.dimension:
            return False
    if filters.entity == "all":
        return include_players or sample.category != "player"
    if filters.entity == "mobs":
        return sample.category == "mob"
    if filters.entity == "items":
        return sample.category == "item"
    if filters.entity == "other":
        return sample.category == "other"
    return sample.type_id.lower() == filters.entity


class _ChunkAccumulator:
    __slots__ = (
        "dimension_key",
        "dimension_name",
        "chunk_x",
        "chunk_z",
        "types",
        "categories",
        "sections",
        "section_positions",
        "item_quantity",
        "min_y",
        "max_y",
    )

    def __init__(self, sample: ActorSample):
        self.dimension_key = sample.dimension_key
        self.dimension_name = sample.dimension_name
        self.chunk_x, self.chunk_z = chunk_coordinates(sample.x, sample.z)
        self.types: Counter[str] = Counter()
        self.categories: Counter[str] = Counter()
        self.sections: Counter[int] = Counter()
        self.section_positions: dict[int, list[float]] = {}
        self.item_quantity = 0
        self.min_y = sample.y
        self.max_y = sample.y

    def add(self, sample: ActorSample) -> None:
        section = math.floor(sample.y / 16.0)
        self.types[sample.type_id] += 1
        self.categories[sample.category] += 1
        self.sections[section] += 1
        position_totals = self.section_positions.setdefault(section, [0.0, 0.0, 0.0])
        position_totals[0] += sample.x
        position_totals[1] += sample.y
        position_totals[2] += sample.z
        self.item_quantity += max(0, sample.item_quantity)
        self.min_y = min(self.min_y, sample.y)
        self.max_y = max(self.max_y, sample.y)

    def finish(self) -> ChunkHotspot:
        total = sum(self.categories.values())
        busiest_section, section_count = sorted(
            self.sections.items(), key=lambda item: (-item[1], item[0])
        )[0]
        sums = self.section_positions[busiest_section]
        return ChunkHotspot(
            dimension_key=self.dimension_key,
            dimension_name=self.dimension_name,
            chunk_x=self.chunk_x,
            chunk_z=self.chunk_z,
            total=total,
            mob_count=self.categories.get("mob", 0),
            item_entity_count=self.categories.get("item", 0),
            player_count=self.categories.get("player", 0),
            other_count=self.categories.get("other", 0),
            item_quantity=self.item_quantity,
            min_y=self.min_y,
            max_y=self.max_y,
            busiest_section_y=busiest_section,
            busiest_section_count=section_count,
            representative_x=sums[0] / section_count,
            representative_y=sums[1] / section_count,
            representative_z=sums[2] / section_count,
            type_counts=tuple(sorted(self.types.items(), key=lambda item: (-item[1], item[0]))),
            category_counts=tuple(
                sorted(self.categories.items(), key=lambda item: (-item[1], item[0]))
            ),
        )


def aggregate_chunks(samples: Iterable[ActorSample]) -> tuple[ChunkHotspot, ...]:
    accumulators: dict[tuple[str, int, int], _ChunkAccumulator] = {}
    for sample in samples:
        chunk_x, chunk_z = chunk_coordinates(sample.x, sample.z)
        key = (sample.dimension_key, chunk_x, chunk_z)
        accumulator = accumulators.get(key)
        if accumulator is None:
            accumulator = _ChunkAccumulator(sample)
            accumulators[key] = accumulator
        accumulator.add(sample)

    chunks = [accumulator.finish() for accumulator in accumulators.values()]
    chunks.sort(
        key=lambda chunk: (
            -chunk.total,
            chunk.dimension_key,
            chunk.chunk_x,
            chunk.chunk_z,
        )
    )
    return tuple(chunks)


def _merge_counts(chunks: Sequence[ChunkHotspot], attribute: str) -> Counter[str]:
    merged: Counter[str] = Counter()
    for chunk in chunks:
        merged.update(dict(getattr(chunk, attribute)))
    return merged


def aggregate_groups(
    chunks: Sequence[ChunkHotspot], dense_chunk_threshold: int
) -> tuple[GroupHotspot, ...]:
    threshold = max(1, int(dense_chunk_threshold))
    eligible = {
        (chunk.dimension_key, chunk.chunk_x, chunk.chunk_z): chunk
        for chunk in chunks
        if chunk.total >= threshold
    }
    unvisited = set(eligible)
    groups: list[GroupHotspot] = []

    for root in sorted(unvisited):
        if root not in unvisited:
            continue
        unvisited.remove(root)
        queue = deque([root])
        component_keys = []
        while queue:
            key = queue.popleft()
            component_keys.append(key)
            dimension_key, chunk_x, chunk_z = key
            for offset_x in (-1, 0, 1):
                for offset_z in (-1, 0, 1):
                    if offset_x == 0 and offset_z == 0:
                        continue
                    neighbor = (dimension_key, chunk_x + offset_x, chunk_z + offset_z)
                    if neighbor in unvisited:
                        unvisited.remove(neighbor)
                        queue.append(neighbor)

        component = [eligible[key] for key in component_keys]
        component.sort(key=lambda chunk: (chunk.chunk_x, chunk.chunk_z))
        peak = sorted(
            component, key=lambda chunk: (-chunk.total, chunk.chunk_x, chunk.chunk_z)
        )[0]
        types = _merge_counts(component, "type_counts")
        categories = _merge_counts(component, "category_counts")
        total = sum(chunk.total for chunk in component)
        groups.append(
            GroupHotspot(
                dimension_key=peak.dimension_key,
                dimension_name=peak.dimension_name,
                total=total,
                chunk_count=len(component),
                min_chunk_x=min(chunk.chunk_x for chunk in component),
                max_chunk_x=max(chunk.chunk_x for chunk in component),
                min_chunk_z=min(chunk.chunk_z for chunk in component),
                max_chunk_z=max(chunk.chunk_z for chunk in component),
                min_y=min(chunk.min_y for chunk in component),
                max_y=max(chunk.max_y for chunk in component),
                average_per_chunk=total / len(component),
                peak_chunk_x=peak.chunk_x,
                peak_chunk_z=peak.chunk_z,
                peak_chunk_count=peak.total,
                representative_x=peak.representative_x,
                representative_y=peak.representative_y,
                representative_z=peak.representative_z,
                mob_count=categories.get("mob", 0),
                item_entity_count=categories.get("item", 0),
                player_count=categories.get("player", 0),
                other_count=categories.get("other", 0),
                item_quantity=sum(chunk.item_quantity for chunk in component),
                type_counts=tuple(sorted(types.items(), key=lambda item: (-item[1], item[0]))),
                category_counts=tuple(
                    sorted(categories.items(), key=lambda item: (-item[1], item[0]))
                ),
            )
        )

    groups.sort(
        key=lambda group: (
            -group.total,
            group.dimension_key,
            group.min_chunk_x,
            group.min_chunk_z,
            group.max_chunk_x,
            group.max_chunk_z,
        )
    )
    return tuple(groups)


def build_rankings(
    samples: Iterable[ActorSample], dense_chunk_threshold: int
) -> tuple[tuple[ChunkHotspot, ...], tuple[GroupHotspot, ...]]:
    chunks = aggregate_chunks(samples)
    return chunks, aggregate_groups(chunks, dense_chunk_threshold)


def paginate(results: Sequence, page: int, per_page: int) -> tuple[Sequence, int]:
    page_size = max(1, int(per_page))
    total_pages = max(1, math.ceil(len(results) / page_size))
    if page < 1 or page > total_pages:
        raise IndexError(f"page must be between 1 and {total_pages}")
    start = (page - 1) * page_size
    return results[start : start + page_size], total_pages


class SnapshotStore:
    """Thread-safe bounded storage for immutable, sender-owned snapshots."""

    def __init__(self, max_retained: int, lifetime_seconds: float):
        self.max_retained = max(1, int(max_retained))
        self.lifetime_seconds = max(1.0, float(lifetime_seconds))
        self._snapshots: OrderedDict[str, HotspotSnapshot] = OrderedDict()
        self._selections: dict[str, SnapshotSelection] = {}
        self._lock = threading.RLock()

    def reconfigure(self, max_retained: int, lifetime_seconds: float) -> None:
        with self._lock:
            self.max_retained = max(1, int(max_retained))
            self.lifetime_seconds = max(1.0, float(lifetime_seconds))
            self._enforce_limit()

    def put(self, snapshot: HotspotSnapshot, mode: str) -> None:
        if mode not in RANKING_MODES:
            raise ValueError(f"unknown ranking mode: {mode}")
        with self._lock:
            self._snapshots[snapshot.scan_id] = snapshot
            self._snapshots.move_to_end(snapshot.scan_id)
            self._selections[snapshot.owner_key] = SnapshotSelection(snapshot.scan_id, mode)
            self._enforce_limit()

    def select_mode(self, owner_key: str, mode: str, now: float) -> HotspotSnapshot:
        if mode not in RANKING_MODES:
            raise ValueError(f"unknown ranking mode: {mode}")
        with self._lock:
            snapshot, selection = self._resolve(owner_key, now)
            self._selections[owner_key] = SnapshotSelection(selection.snapshot_id, mode)
            return snapshot

    def get_selected(
        self, owner_key: str, now: float
    ) -> tuple[HotspotSnapshot, SnapshotSelection]:
        with self._lock:
            return self._resolve(owner_key, now)

    def get_for_refresh(self, owner_key: str) -> tuple[HotspotSnapshot, SnapshotSelection]:
        """Return query metadata even when its results are too old to inspect."""

        with self._lock:
            selection = self._selections.get(owner_key)
            if selection is None:
                raise LookupError("no saved hotspot query; run /entityinfo hotspots")
            snapshot = self._snapshots.get(selection.snapshot_id)
            if snapshot is None or snapshot.owner_key != owner_key:
                raise LookupError("saved hotspot query is unavailable; run /entityinfo hotspots")
            return snapshot, selection

    def get_rank(
        self, owner_key: str, rank: int, now: float
    ) -> tuple[HotspotSnapshot, SnapshotSelection, ChunkHotspot | GroupHotspot]:
        with self._lock:
            snapshot, selection = self._resolve(owner_key, now)
            results = snapshot.results(selection.mode)
            if rank < 1 or rank > len(results):
                raise IndexError(f"rank must be between 1 and {len(results)}")
            return snapshot, selection, results[rank - 1]

    def remove_owner(self, owner_key: str) -> None:
        with self._lock:
            self._selections.pop(owner_key, None)
            for scan_id, snapshot in list(self._snapshots.items()):
                if snapshot.owner_key == owner_key:
                    del self._snapshots[scan_id]

    def purge_expired(self, now: float) -> None:
        with self._lock:
            expired = [
                scan_id
                for scan_id, snapshot in self._snapshots.items()
                if now - snapshot.completed_at > self.lifetime_seconds
            ]
            for scan_id in expired:
                del self._snapshots[scan_id]
            self._remove_dangling_selections()

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._selections.clear()

    def _resolve(
        self, owner_key: str, now: float
    ) -> tuple[HotspotSnapshot, SnapshotSelection]:
        selection = self._selections.get(owner_key)
        if selection is None:
            raise LookupError("no saved hotspot scan; run /entityinfo hotspots")
        snapshot = self._snapshots.get(selection.snapshot_id)
        if snapshot is None or snapshot.owner_key != owner_key:
            self._selections.pop(owner_key, None)
            raise LookupError("saved hotspot scan is unavailable; run /entityinfo hotspots refresh")
        if now - snapshot.completed_at > self.lifetime_seconds:
            raise TimeoutError("saved hotspot scan expired; run /entityinfo hotspots refresh")
        return snapshot, selection

    def _enforce_limit(self) -> None:
        while len(self._snapshots) > self.max_retained:
            self._snapshots.popitem(last=False)
        self._remove_dangling_selections()

    def _remove_dangling_selections(self) -> None:
        available = set(self._snapshots)
        for owner_key, selection in list(self._selections.items()):
            if selection.snapshot_id not in available:
                del self._selections[owner_key]
