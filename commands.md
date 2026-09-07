# Onistone Essentials entity-hotspot commands

This guide covers the loaded-entity hotspot additions to `/entityinfo`. The complete command suite remains listed in the [README](README.md#commands-and-permissions).

## Quick workflow

```text
/entityinfo hotspots
/entityinfo hotspots groups
/entityinfo hotspots detail 1
/entityinfo tp 1
```

The initial command starts a loaded-actor sample and prints the busiest chunks. Switching to groups reuses the same sample, detail expands absolute rank `1`, and `tp` searches for a conservative safe standing position near that same saved result.

## Syntax

| Command | Purpose |
|---|---|
| `/entityinfo` | Preserve the existing player-only targeted entity inspection. |
| `/entityinfo list` | Preserve the existing totals for currently exposed loaded actor types. |
| `/entityinfo list <page>` | Show another type-total page. |
| `/entityinfo hotspots` | Scan on demand when needed, then show page 1 of the busiest loaded chunks. |
| `/entityinfo hotspots <page>` | Show an absolute page of the selected saved scan's chunk ranking. |
| `/entityinfo hotspots chunks [page]` | Select the individual vertical chunk-column ranking. |
| `/entityinfo hotspots groups [page]` | Select connected groups of dense neighboring chunks. |
| `/entityinfo hotspots detail <rank>` | Show category/type counts, bounds, Y range, peak data, and the inspection anchor for an absolute rank. |
| `/entityinfo hotspots refresh` | Start a new sample using the selected mode and filters, subject to cooldown and concurrency settings. |
| `/entityinfo hotspots help` | Show a compact in-game explanation and syntax list. |
| `/entityinfo hotspots filter <chunks\|groups> <dimension> <type-or-category> [page]` | Run or reuse a filtered query. |
| `/entityinfo tp <rank>` | Player-only teleport to a loaded, validated standing position near the selected rank. |

Examples:

```text
/entityinfo hotspots filter groups overworld items
/entityinfo hotspots filter chunks all minecraft:chicken
/entityinfo hotspots filter chunks my_pack:moon my_pack:clockwork_golem 2
```

`<dimension>` accepts `all`, the common `overworld`, `nether`, and `the_end` aliases, or an exact custom dimension name. `<type-or-category>` accepts:

- `all`: all eligible actors (non-player by default)
- `mobs`: actors exposed as Endstone `Mob`, excluding players
- `items`: dropped Endstone `Item` actors
- `other`: non-player actors that are neither `Mob` nor `Item`
- a full identifier such as `minecraft:chicken` or `my_pack:clockwork_golem`

Filters are applied before per-chunk totals, the dense threshold, and group construction.

## Permissions

All `/entityinfo` overloads retain the command's existing parent permission:

```text
onistone.command.entityinfo
```

Hotspot scans, pages, modes, filters, details, refresh, and help additionally check:

```text
onistone.command.entityinfo.hotspots
```

Teleport additionally checks this separate permission at execution time:

```text
onistone.command.entityinfo.hotspots.teleport
```

Both new permissions are explicitly registered with operator-only defaults. The teleport permission is not a command-level requirement for ordinary `/entityinfo` or hotspot viewing. Console can scan and view; command blocks remain refused; teleport is player-only.

## Counting and ranking

- Only actors currently returned by the loaded-actor API are sampled. The scanner never reads offline world data or intentionally loads a chunk.
- Players are excluded unless `include_players` is enabled. Named, tamed, and custom entities are not otherwise protected or omitted.
- A dropped stack is one item entity. Its stack amount is shown only as a supplemental quantity.
- Stable actor IDs prevent duplicate counting. Invalid, inaccessible, despawned, or dimension-changing actors are skipped and make coverage visibly incomplete.
- Chunk coordinates use `floor(x / 16)` and `floor(z / 16)`, including for negative positions.
- Equal totals use dimension and coordinate tie-breakers so ordering and pagination remain deterministic.
- A chunk result represents the entire vertical column. The busiest observed 16-block Y section supplies its inspection anchor.
- Group candidates must meet `dense_chunk_threshold` after filtering. Eight-neighbor adjacency includes diagonals, never crosses dimensions, and includes qualifying standalone chunks.
- Group totals use every eligible chunk, not only a visible page. The inspection anchor comes from the group's highest-count chunk rather than a possibly empty weighted center.

Each header reports scan ID, completion time and age, examined/matched/skipped counts, duration, page, completion status, and a loaded-only notice. Absolute ranks, pages, details, and teleports remain bound to that administrator's immutable snapshot. An expired snapshot refuses the action and tells the administrator to refresh.

Every completed scan also replaces `plugins/onistone_essentials/entity_hotspot_report.md`. This Markdown file contains the full scan summary, all ranked chunks, all dense groups, coordinates, category totals, Y ranges, and entity-type counts. It is written atomically on a background worker and does not accumulate unbounded historical files.

## Configuration

Settings live at `modules.entity_hotspots` in `plugins/onistone_essentials/config.json`.

| Setting | Default | Meaning |
|---|---:|---|
| `enabled` | `true` | Enables hotspot subcommands. |
| `write_report_file` | `true` | Writes the latest complete or incomplete scan to `entity_hotspot_report.md` in the plugin data folder. |
| `results_per_page` | `5` | Compact results per chat page, clamped to 1–10. |
| `include_players` | `false` | Includes players in `all` scans when enabled. |
| `scan_cooldown_seconds` | `15` | Per-sender delay between new scans. |
| `snapshot_lifetime_seconds` | `300` | Saved-result lifetime. |
| `max_retained_snapshots` | `16` | Global bounded snapshot count. |
| `max_concurrent_scans` | `1` | Bounded simultaneous scan requests. |
| `max_actors` | `20000` | Maximum actor references examined per scan. |
| `max_scan_seconds` | `8.0` | Maximum sampling-window duration. |
| `actors_per_tick` | `750` | Live actor references validated and detached per scheduler tick. |
| `dense_chunk_threshold` | `10` | Matching entities required for a chunk to enter group mode. |
| `teleport_enabled` | `true` | Enables explicit inspection teleports. |
| `teleport_horizontal_radius` | `4` | Block radius searched around the saved anchor. |
| `teleport_vertical_radius` | `32` | Vertical distance searched, within conservative dimension bounds. |
| `teleport_max_candidates` | `512` | Hard cap on candidate standing positions checked. |

Missing defaults are recursively added on startup; configured values are not overwritten.

## API and safety limits

Endstone 0.11.9 supplies `Level.actors`, stable actor IDs, validity state, actor dimensions/locations, `Dimension.loaded_chunks`, and block lookup. Its actor-list acquisition is indivisible, so the plugin measures and reports that call but cannot enforce a hard per-tick budget on it. `actors_per_tick` applies after acquisition. A scan spanning multiple ticks samples a changing world rather than creating an atomic server snapshot.

The supported API does not expose a generic block collision/passability property or `is_chunk_loaded`. Teleport validation therefore snapshots `Dimension.loaded_chunks`, refuses an unloaded hotspot before block access, limits every block lookup to those coordinates, requires two explicit air blocks, applies conservative dimension height bounds, and rejects known hazards and unsupported floor types. If safety cannot be verified, the player is not moved and receives the saved coordinates and reason. No block is placed and no protection or game-mode state is changed.
