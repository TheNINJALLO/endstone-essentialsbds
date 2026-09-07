from __future__ import annotations

from endstone_primebds.utils.entity_hotspot_report import (
    REPORT_FILENAME,
    render_hotspot_report,
    write_hotspot_report,
)
from endstone_primebds.utils.entity_hotspots import (
    ActorSample,
    HotspotFilter,
    HotspotSnapshot,
    build_rankings,
)


def snapshot() -> HotspotSnapshot:
    samples = (
        ActorSample(
            "mob-1",
            "minecraft:zombie",
            "mob",
            "overworld",
            "Overworld",
            17.5,
            64.0,
            -1.0,
        ),
        ActorSample(
            "item-1",
            "minecraft:item",
            "item",
            "overworld",
            "Overworld",
            18.0,
            65.0,
            -2.0,
            32,
        ),
    )
    chunks, groups = build_rankings(samples, dense_chunk_threshold=1)
    return HotspotSnapshot(
        scan_id="EH-0042",
        owner_key="player:admin",
        filters=HotspotFilter.create(),
        started_at=1_700_000_000.0,
        completed_at=1_700_000_001.25,
        duration_ms=1_250.0,
        acquisition_ms=2.5,
        collection_ticks=2,
        actors_available=2,
        actors_examined=2,
        actors_matched=2,
        actors_skipped=0,
        duplicate_actors=0,
        complete=True,
        limit_reason="",
        chunks=chunks,
        groups=groups,
    )


def test_report_contains_full_readable_chunk_and_group_results():
    report = render_hotspot_report(snapshot())

    assert "# Onistone Essentials Entity Hotspot Report" in report
    assert "| Scan ID | EH-0042 |" in report
    assert "## Chunk hotspots (1)" in report
    assert "minecraft:zombie x1" in report
    assert "## Dense groups (1)" in report
    assert "Dropped item quantity" in report


def test_report_atomically_replaces_the_latest_file(tmp_path):
    expected = render_hotspot_report(snapshot())
    destination = write_hotspot_report(snapshot(), tmp_path)

    assert destination == tmp_path / REPORT_FILENAME
    assert destination.read_text(encoding="utf-8") == expected
    assert list(tmp_path.glob("*.tmp")) == []
