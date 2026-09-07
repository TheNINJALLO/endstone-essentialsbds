from __future__ import annotations

import pytest

from endstone_primebds.utils.entity_hotspots import (
    ActorSample,
    HotspotFilter,
    HotspotSettings,
    HotspotSnapshot,
    SnapshotStore,
    aggregate_chunks,
    build_rankings,
    chunk_coordinates,
    paginate,
    sample_matches,
)


def actor(
    stable_id: str,
    x: float,
    z: float,
    *,
    dimension: str = "overworld",
    type_id: str = "minecraft:chicken",
    category: str = "mob",
    y: float = 64.0,
    quantity: int = 0,
) -> ActorSample:
    return ActorSample(
        stable_id,
        type_id,
        category,
        dimension,
        dimension,
        x,
        y,
        z,
        quantity,
    )


@pytest.mark.parametrize(
    ("coordinate", "expected"),
    [
        (0, 0),
        (15.999, 0),
        (16, 1),
        (-0.001, -1),
        (-1, -1),
        (-16, -1),
        (-17, -2),
    ],
)
def test_floor_based_chunk_boundaries(coordinate, expected):
    assert chunk_coordinates(coordinate, coordinate) == (expected, expected)


def test_same_coordinates_in_different_dimensions_never_merge():
    chunks = aggregate_chunks(
        [actor("a", 1, 1), actor("b", 1, 1, dimension="nether")]
    )

    assert len(chunks) == 2
    assert {(chunk.dimension_key, chunk.total) for chunk in chunks} == {
        ("overworld", 1),
        ("nether", 1),
    }


def test_endstone_dimension_aliases_match_runtime_names():
    end_actor = actor("end", 1, 1, dimension="TheEnd")
    nether_actor = actor("nether", 1, 1, dimension="minecraft:the_nether")

    assert sample_matches(end_actor, HotspotFilter.create("the_end", "all"), False)
    assert sample_matches(nether_actor, HotspotFilter.create("nether", "all"), False)


def test_empty_and_one_entity_rankings():
    empty_chunks, empty_groups = build_rankings([], 1)
    assert empty_chunks == ()
    assert empty_groups == ()

    chunks, groups = build_rankings([actor("one", 2, 3)], 1)
    assert len(chunks) == 1
    assert chunks[0].total == 1
    assert len(groups) == 1
    assert groups[0].chunk_count == 1


def test_player_exclusion_and_custom_namespaced_filter():
    player = actor(
        "player", 1, 1, type_id="minecraft:player", category="player"
    )
    custom = actor("custom", 2, 2, type_id="my_pack:clockwork_golem")
    all_filter = HotspotFilter.create("all", "all")
    custom_filter = HotspotFilter.create("all", "my_pack:clockwork_golem")

    assert sample_matches(player, all_filter, include_players=False) is False
    assert sample_matches(player, all_filter, include_players=True) is True
    assert sample_matches(custom, custom_filter, include_players=False) is True
    with pytest.raises(ValueError):
        HotspotFilter.create("all", "chicken")


def test_dropped_item_entity_count_does_not_use_stack_quantity():
    chunks = aggregate_chunks(
        [
            actor(
                "drop-1", 1, 1, type_id="minecraft:item", category="item", quantity=64
            ),
            actor(
                "drop-2", 2, 2, type_id="minecraft:item", category="item", quantity=3
            ),
        ]
    )

    assert chunks[0].total == 2
    assert chunks[0].item_entity_count == 2
    assert chunks[0].item_quantity == 67


def test_dense_groups_cross_borders_use_diagonals_and_keep_isolated_chunks():
    samples = [
        actor("a", 15.9, 1),
        actor("b", 16.0, 1),
        actor("c", 32.0, 16.0),  # diagonal from chunk 1,0
        actor("isolated", 160.0, 160.0),
    ]
    _chunks, groups = build_rankings(samples, 1)

    assert [group.chunk_count for group in groups] == [3, 1]
    assert groups[0].total == 3
    assert (groups[0].min_chunk_x, groups[0].max_chunk_x) == (0, 2)


def test_long_connected_group_is_near_linear_and_reports_extent():
    samples = [actor(str(index), index * 16.0, 0) for index in range(40)]
    _chunks, groups = build_rankings(samples, 1)

    assert len(groups) == 1
    assert groups[0].chunk_count == 40
    assert groups[0].min_chunk_x == 0
    assert groups[0].max_chunk_x == 39


def test_filters_apply_before_dense_threshold_and_grouping():
    samples = [
        actor("i1", 1, 1, type_id="minecraft:item", category="item"),
        actor("i2", 2, 2, type_id="minecraft:item", category="item"),
        actor("i3", 17, 1, type_id="minecraft:item", category="item"),
        actor("cow", 18, 1, type_id="minecraft:cow", category="mob"),
    ]
    filters = HotspotFilter.create("all", "items")
    filtered = [sample for sample in samples if sample_matches(sample, filters, False)]
    _chunks, groups = build_rankings(filtered, 2)

    assert len(groups) == 1
    assert groups[0].chunk_count == 1
    assert groups[0].total == 2


def test_rankings_and_absolute_pagination_are_deterministic():
    samples = [
        actor("z", 32, 0),
        actor("x", 0, 0),
        actor("y", 16, 0),
    ]
    first = aggregate_chunks(samples)
    second = aggregate_chunks(reversed(samples))

    assert [(chunk.chunk_x, chunk.chunk_z) for chunk in first] == [(0, 0), (1, 0), (2, 0)]
    assert first == second
    page, pages = paginate(first, 2, 2)
    assert pages == 2
    assert [(chunk.chunk_x, chunk.chunk_z) for chunk in page] == [(2, 0)]


def snapshot(scan_id: str, owner: str, completed: float) -> HotspotSnapshot:
    chunks, groups = build_rankings([actor(f"{scan_id}-actor", 1, 1)], 1)
    return HotspotSnapshot(
        scan_id=scan_id,
        owner_key=owner,
        filters=HotspotFilter.create(),
        started_at=completed - 1,
        completed_at=completed,
        duration_ms=1,
        acquisition_ms=0.1,
        collection_ticks=1,
        actors_available=1,
        actors_examined=1,
        actors_matched=1,
        actors_skipped=0,
        duplicate_actors=0,
        complete=True,
        limit_reason="",
        chunks=chunks,
        groups=groups,
    )


def test_each_administrator_has_an_independent_selection_and_rank():
    store = SnapshotStore(max_retained=4, lifetime_seconds=30)
    store.put(snapshot("EH-1", "admin-a", 100), "chunks")
    store.put(snapshot("EH-2", "admin-b", 101), "groups")

    assert store.get_selected("admin-a", 102)[0].scan_id == "EH-1"
    assert store.get_selected("admin-b", 102)[1].mode == "groups"
    assert store.get_rank("admin-a", 1, 102)[2].total == 1
    with pytest.raises(IndexError):
        store.get_rank("admin-a", 2, 102)


def test_expired_snapshots_are_not_silently_replaced():
    store = SnapshotStore(max_retained=2, lifetime_seconds=10)
    store.put(snapshot("EH-1", "admin", 100), "chunks")

    with pytest.raises(TimeoutError, match="refresh"):
        store.get_selected("admin", 111)
    with pytest.raises(TimeoutError):
        store.get_selected("admin", 111)
    assert store.get_for_refresh("admin")[0].scan_id == "EH-1"


def test_configuration_values_are_validated_and_clamped():
    settings = HotspotSettings.from_mapping(
        {
            "results_per_page": 999,
            "max_actors": "bad",
            "enabled": "not-a-boolean",
            "write_report_file": False,
            "teleport_max_candidates": 1,
        }
    )

    assert settings.results_per_page == 10
    assert settings.max_actors == 20_000
    assert settings.enabled is True
    assert settings.write_report_file is False
    assert settings.teleport_max_candidates == 16
