"""Human-readable file reports for loaded-entity hotspot snapshots."""

from __future__ import annotations

from datetime import datetime
from html import escape
import math
import os
from pathlib import Path
import threading

from endstone_primebds.utils.entity_hotspots import (
    ChunkHotspot,
    GroupHotspot,
    HotspotSnapshot,
)


REPORT_FILENAME = "entity_hotspot_report.md"


def _escape_cell(value: object) -> str:
    return (
        escape(str(value), quote=False)
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _timestamp(value: float) -> str:
    return datetime.fromtimestamp(value).astimezone().isoformat(timespec="seconds")


def _coordinates(result: ChunkHotspot | GroupHotspot) -> str:
    return ", ".join(
        str(math.floor(value))
        for value in (
            result.representative_x,
            result.representative_y,
            result.representative_z,
        )
    )


def _type_counts(values: tuple[tuple[str, int], ...]) -> str:
    if not values:
        return "none"
    return ", ".join(f"{entity_type} x{count}" for entity_type, count in values)


def render_hotspot_report(snapshot: HotspotSnapshot) -> str:
    """Render every chunk and group in a snapshot as readable Markdown."""

    status = "Complete" if snapshot.complete else f"INCOMPLETE: {snapshot.limit_reason}"
    lines = [
        "# Onistone Essentials Entity Hotspot Report",
        "",
        "> This report contains loaded entities only. A high count is a diagnostic lead, not proof of server lag.",
        "",
        "## Scan summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Scan ID | {_escape_cell(snapshot.scan_id)} |",
        f"| Requested by | {_escape_cell(snapshot.owner_key)} |",
        f"| Started | {_timestamp(snapshot.started_at)} |",
        f"| Completed | {_timestamp(snapshot.completed_at)} |",
        f"| Status | {_escape_cell(status)} |",
        f"| Filters | dimension={_escape_cell(snapshot.filters.dimension)}, entities={_escape_cell(snapshot.filters.entity)} |",
        f"| Actors available | {snapshot.actors_available:,} |",
        f"| Actors examined | {snapshot.actors_examined:,} |",
        f"| Actors matched | {snapshot.actors_matched:,} |",
        f"| Actors skipped | {snapshot.actors_skipped:,} |",
        f"| Duplicate actors ignored | {snapshot.duplicate_actors:,} |",
        f"| Total duration | {snapshot.duration_ms:,.1f} ms |",
        f"| Actor-list acquisition | {snapshot.acquisition_ms:,.1f} ms |",
        f"| Collection ticks | {snapshot.collection_ticks:,} |",
        f"| Ranked chunks | {len(snapshot.chunks):,} |",
        f"| Ranked dense groups | {len(snapshot.groups):,} |",
        "",
        f"## Chunk hotspots ({len(snapshot.chunks):,})",
        "",
    ]

    if snapshot.chunks:
        lines.extend(
            [
                "| Rank | Dimension | Chunk X, Z | Near X, Y, Z | Entities | Mobs | Item entities | Players | Other | Dropped item quantity | Y range | Busiest Y section | Top entity types |",
                "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for rank, chunk in enumerate(snapshot.chunks, start=1):
            lines.append(
                f"| {rank} | {_escape_cell(chunk.dimension_name)} | "
                f"{chunk.chunk_x}, {chunk.chunk_z} | {_coordinates(chunk)} | "
                f"{chunk.total:,} | {chunk.mob_count:,} | {chunk.item_entity_count:,} | "
                f"{chunk.player_count:,} | {chunk.other_count:,} | {chunk.item_quantity:,} | "
                f"{math.floor(chunk.min_y)}..{math.floor(chunk.max_y)} | "
                f"{chunk.busiest_section_y} ({chunk.busiest_section_count:,}) | "
                f"{_escape_cell(_type_counts(chunk.type_counts))} |"
            )
    else:
        lines.append("_No loaded entities matched this scan._")

    lines.extend(["", f"## Dense groups ({len(snapshot.groups):,})", ""])
    if snapshot.groups:
        lines.extend(
            [
                "| Rank | Dimension | Chunk extent | Chunks | Entities | Average/chunk | Peak chunk | Near X, Y, Z | Mobs | Item entities | Players | Other | Dropped item quantity | Y range | Top entity types |",
                "|---:|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for rank, group in enumerate(snapshot.groups, start=1):
            extent = (
                f"X {group.min_chunk_x}..{group.max_chunk_x}, "
                f"Z {group.min_chunk_z}..{group.max_chunk_z}"
            )
            peak = (
                f"{group.peak_chunk_x}, {group.peak_chunk_z} "
                f"({group.peak_chunk_count:,})"
            )
            lines.append(
                f"| {rank} | {_escape_cell(group.dimension_name)} | {extent} | "
                f"{group.chunk_count:,} | {group.total:,} | {group.average_per_chunk:,.1f} | "
                f"{peak} | {_coordinates(group)} | {group.mob_count:,} | "
                f"{group.item_entity_count:,} | {group.player_count:,} | "
                f"{group.other_count:,} | {group.item_quantity:,} | "
                f"{math.floor(group.min_y)}..{math.floor(group.max_y)} | "
                f"{_escape_cell(_type_counts(group.type_counts))} |"
            )
    else:
        lines.append("_No chunks met the configured dense-group threshold._")

    lines.extend(
        [
            "",
            "---",
            "Generated automatically by Onistone Essentials. The next completed hotspot scan replaces this report.",
            "",
        ]
    )
    return "\n".join(lines)


def write_hotspot_report(
    snapshot: HotspotSnapshot, report_directory: str | os.PathLike[str]
) -> Path:
    """Atomically replace the latest report and return its path."""

    directory = Path(report_directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / REPORT_FILENAME
    temporary = directory / (
        f".{REPORT_FILENAME}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as report_file:
            report_file.write(render_hotspot_report(snapshot))
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return destination
