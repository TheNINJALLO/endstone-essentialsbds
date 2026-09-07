from __future__ import annotations

from collections import Counter
from datetime import datetime
import math
from typing import TYPE_CHECKING

from endstone import Player
from endstone.actor import Item, Mob
from endstone.command import CommandSender
from endstone.level import Location

try:
    from endstone.command import BlockCommandSender
except ImportError:  # Endstone builds where this optional sender is not exported
    BlockCommandSender = None

from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.entity_hotspot_teleport import find_safe_inspection_position
from endstone_primebds.utils.entity_hotspots import (
    ActorSample,
    ChunkHotspot,
    GroupHotspot,
    HotspotFilter,
    HotspotSnapshot,
    canonical_dimension,
    paginate,
)
from endstone_primebds.utils.target_selector_util import get_target_entity

if TYPE_CHECKING:
    from endstone_primebds.primebds import OnistoneEssentials


HOTSPOT_PERMISSION = "onistone.command.entityinfo.hotspots"
TELEPORT_PERMISSION = "onistone.command.entityinfo.hotspots.teleport"


command, permission = create_command(
    "entityinfo",
    "Inspect entities and locate loaded-entity hotspots",
    [
        "/entityinfo",
        "/entityinfo (list)<entity_action: entity_action> [page: int]",
        "/entityinfo (hotspots)<hotspots_action: hotspots_action> [page: int]",
        "/entityinfo (hotspots)<hotspots_action: hotspots_action> (chunks|groups)<ranking_mode: ranking_mode> [page: int]",
        "/entityinfo (hotspots)<hotspots_action: hotspots_action> (detail)<detail_action: detail_action> <rank: int>",
        "/entityinfo (hotspots)<hotspots_action: hotspots_action> (refresh|help)<hotspot_utility: hotspot_utility>",
        "/entityinfo (hotspots)<hotspots_action: hotspots_action> (filter)<filter_action: filter_action> (chunks|groups)<filter_mode: filter_mode> <dimension: string> <entity_filter: string> [page: int]",
        "/entityinfo (tp)<teleport_action: teleport_action> <rank: int>",
    ],
    ["onistone.command.entityinfo"],
)

# create_command intentionally registers only its command-level permission. These
# subcommand permissions are separate so teleport is not required for scans.
permission.update(
    {
        HOTSPOT_PERMISSION: {
            "description": "Allows loaded-entity hotspot scans and snapshot viewing",
            "default": "op",
        },
        TELEPORT_PERMISSION: {
            "description": "Allows teleporting to a validated entity hotspot",
            "default": "op",
        },
    }
)


def _has_permission(sender: CommandSender, permission_name: str) -> bool:
    try:
        return bool(sender.has_permission(permission_name))
    except Exception:
        return False


def _require_permission(sender: CommandSender, permission_name: str) -> bool:
    if _has_permission(sender, permission_name):
        return True
    sender.send_message(f"§cYou do not have permission: {permission_name}")
    return False


def _safe_int(value: str, label: str, sender: CommandSender) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        sender.send_message(f"§c{label} must be a positive whole number.")
        return None
    if result < 1:
        sender.send_message(f"§c{label} must be at least 1.")
        return None
    return result


def _dimension_identity(dimension) -> tuple[str, str]:
    name = str(dimension.name)
    return canonical_dimension(name), name


def sample_loaded_actor(actor) -> ActorSample | None:
    """Detach one still-valid actor into primitives on the server thread."""

    if not bool(actor.is_valid) or bool(actor.is_dead):
        return None
    stable_id = str(actor.id)
    first_dimension = actor.dimension
    first_key, first_name = _dimension_identity(first_dimension)
    location = actor.location
    location_dimension = location.dimension
    location_key, _ = _dimension_identity(location_dimension)
    second_dimension = actor.dimension
    second_key, _ = _dimension_identity(second_dimension)
    if not bool(actor.is_valid) or first_key != location_key or first_key != second_key:
        return None

    x, y, z = float(location.x), float(location.y), float(location.z)
    if not all(math.isfinite(value) for value in (x, y, z)):
        return None
    type_id = str(actor.type).strip().lower()
    if not type_id:
        return None

    item_quantity = 0
    if isinstance(actor, Player):
        category = "player"
    elif isinstance(actor, Item):
        category = "item"
        try:
            item_quantity = max(0, int(actor.item_stack.amount))
        except Exception:
            item_quantity = 0
    elif isinstance(actor, Mob):
        category = "mob"
    else:
        category = "other"

    return ActorSample(
        stable_id=stable_id,
        type_id=type_id,
        category=category,
        dimension_key=first_key,
        dimension_name=first_name,
        x=x,
        y=y,
        z=z,
        item_quantity=item_quantity,
    )


def _short_types(type_counts: tuple[tuple[str, int], ...], limit: int = 3) -> str:
    if not type_counts:
        return "none"
    return ", ".join(f"{entity_type}×{count}" for entity_type, count in type_counts[:limit])


def _filter_label(filters: HotspotFilter) -> str:
    return f"dimension={filters.dimension}, entities={filters.entity}"


def _result_coordinates(result: ChunkHotspot | GroupHotspot) -> str:
    return (
        f"{math.floor(result.representative_x)}, "
        f"{math.floor(result.representative_y)}, "
        f"{math.floor(result.representative_z)}"
    )


def _show_snapshot(
    self: "OnistoneEssentials",
    sender: CommandSender,
    snapshot: HotspotSnapshot,
    mode: str,
    page: int,
) -> bool:
    settings = self.entity_hotspot_service.settings()
    results = snapshot.results(mode)
    try:
        page_items, total_pages = paginate(results, page, settings.results_per_page)
    except IndexError as exc:
        sender.send_message(f"§c{exc}. This saved scan was not refreshed.")
        return False

    age = max(0, int(self.entity_hotspot_service.current_time() - snapshot.completed_at))
    completed = datetime.fromtimestamp(snapshot.completed_at).strftime("%H:%M:%S")
    status = "complete" if snapshot.complete else f"INCOMPLETE: {snapshot.limit_reason}"
    sender.send_message(
        f"§eEntity Hotspots §7[{mode}] §f{_filter_label(snapshot.filters)}\n"
        f"§7Scan §f{snapshot.scan_id} §7| completed §f{completed} §7({age}s ago) | "
        f"page §f{page}/{total_pages}\n"
        f"§7Examined §f{snapshot.actors_examined}/{snapshot.actors_available} §7| matched "
        f"§f{snapshot.actors_matched} §7| skipped §f{snapshot.actors_skipped} §7| "
        f"§f{snapshot.duration_ms:.1f}ms §7across {snapshot.collection_ticks} tick(s)\n"
        f"§7Status: §f{status} §8| §6Loaded entities only; high count is a diagnostic lead."
    )
    if not results:
        if mode == "groups":
            sender.send_message(
                f"§7No chunks met the configured dense threshold ({settings.dense_chunk_threshold})."
            )
        else:
            sender.send_message("§7No loaded entities matched this query.")
        return True

    start_rank = (page - 1) * settings.results_per_page + 1
    for offset, result in enumerate(page_items):
        rank = start_rank + offset
        coordinates = _result_coordinates(result)
        if isinstance(result, ChunkHotspot):
            sender.send_message(
                f"§b#{rank} §f{result.dimension_name} §7chunk "
                f"({result.chunk_x}, {result.chunk_z}) §e{result.total} entities\n"
                f"  §7near {coordinates} | {_short_types(result.type_counts)}"
            )
        else:
            sender.send_message(
                f"§b#{rank} §f{result.dimension_name} §e{result.total} entities §7in "
                f"{result.chunk_count} connected dense chunks\n"
                f"  §7extent X {result.min_chunk_x}..{result.max_chunk_x}, Z "
                f"{result.min_chunk_z}..{result.max_chunk_z} | peak "
                f"({result.peak_chunk_x}, {result.peak_chunk_z})={result.peak_chunk_count} | "
                f"near {coordinates}\n  §7{_short_types(result.type_counts)}"
            )
    sender.send_message(
        "§8Use /entityinfo hotspots detail <rank> or /entityinfo tp <rank>."
    )
    return True


def _send_scan_result(
    self: "OnistoneEssentials",
    sender: CommandSender,
    snapshot: HotspotSnapshot | None,
    error: str | None,
    mode: str,
    page: int,
) -> None:
    if isinstance(sender, Player):
        try:
            if not sender.is_valid:
                return
        except Exception:
            return
    if error:
        sender.send_message(f"§cEntity hotspot scan failed: {error}")
        return
    if snapshot is not None:
        _show_snapshot(self, sender, snapshot, mode, page)


def _begin_scan(
    self: "OnistoneEssentials",
    sender: CommandSender,
    mode: str,
    filters: HotspotFilter,
    page: int,
) -> bool:
    owner_key = self.entity_hotspot_service.sender_key(sender)
    started, message = self.entity_hotspot_service.start_scan(
        owner_key,
        mode,
        filters,
        sample_loaded_actor,
        lambda snapshot, error, _ignored_page: _send_scan_result(
            self, sender, snapshot, error, mode, page
        ),
    )
    sender.send_message(("§a" if started else "§c") + message)
    return started


def _reuse_or_scan(
    self: "OnistoneEssentials",
    sender: CommandSender,
    mode: str,
    filters: HotspotFilter,
    page: int,
) -> bool:
    owner_key = self.entity_hotspot_service.sender_key(sender)
    try:
        snapshot, _selection = self.entity_hotspot_service.get_selected(owner_key)
    except (LookupError, TimeoutError):
        return _begin_scan(self, sender, mode, filters, page)
    if snapshot.filters != filters:
        return _begin_scan(self, sender, mode, filters, page)
    self.entity_hotspot_service.select_mode(owner_key, mode)
    return _show_snapshot(self, sender, snapshot, mode, page)


def _view_selected(
    self: "OnistoneEssentials", sender: CommandSender, mode: str, page: int
) -> bool:
    owner_key = self.entity_hotspot_service.sender_key(sender)
    try:
        snapshot = self.entity_hotspot_service.select_mode(owner_key, mode)
    except (LookupError, TimeoutError) as exc:
        sender.send_message(f"§c{exc}")
        return False
    return _show_snapshot(self, sender, snapshot, mode, page)


def _show_detail(self: "OnistoneEssentials", sender: CommandSender, rank: int) -> bool:
    owner_key = self.entity_hotspot_service.sender_key(sender)
    try:
        snapshot, selection, result = self.entity_hotspot_service.get_rank(owner_key, rank)
    except (LookupError, TimeoutError, IndexError) as exc:
        sender.send_message(f"§c{exc}")
        return False

    categories = (
        f"mobs={result.mob_count}, items={result.item_entity_count}, "
        f"players={result.player_count}, other={result.other_count}"
    )
    types = _short_types(result.type_counts, 12)
    remaining = max(0, len(result.type_counts) - 12)
    extra = f" (+{remaining} more types)" if remaining else ""
    lines = [
        f"§eHotspot detail §b#{rank} §7[{selection.mode}] scan §f{snapshot.scan_id}",
        f"§7Dimension: §f{result.dimension_name} §7| matching entities: §f{result.total}",
        f"§7Categories: §f{categories}",
        f"§7Observed Y: §f{math.floor(result.min_y)}..{math.floor(result.max_y)} "
        f"§7| inspection anchor: §f{_result_coordinates(result)}",
    ]
    if result.item_entity_count:
        lines.append(
            f"§7Dropped-item entities: §f{result.item_entity_count} §7| supplemental stack quantity: "
            f"§f{result.item_quantity}"
        )
    if isinstance(result, ChunkHotspot):
        section_min = result.busiest_section_y * 16
        lines.append(
            f"§7Chunk: §f({result.chunk_x}, {result.chunk_z}) §7| busiest vertical section: "
            f"§fY {section_min}..{section_min + 15} ({result.busiest_section_count})"
        )
        lines.append("§8This result covers a vertical chunk column, not an exact 3D cluster.")
    else:
        lines.append(
            f"§7Connected dense chunks: §f{result.chunk_count} §7| average: "
            f"§f{result.average_per_chunk:.1f}/chunk"
        )
        lines.append(
            f"§7Extent: §fX {result.min_chunk_x}..{result.max_chunk_x}, Z "
            f"{result.min_chunk_z}..{result.max_chunk_z} §7| peak: §f"
            f"({result.peak_chunk_x}, {result.peak_chunk_z})={result.peak_chunk_count}"
        )
        lines.append(
            "§8Groups use 8-neighbor chunk adjacency and can form long chains; they are not radius clusters."
        )
    lines.append(f"§7Types: §f{types}{extra}")
    if snapshot.duplicate_actors:
        lines.append(f"§7Duplicate actor IDs ignored: §f{snapshot.duplicate_actors}")
    lines.append(
        f"§8Loaded entities only; scan acquisition {snapshot.acquisition_ms:.1f}ms and sampling "
        f"spanned {snapshot.collection_ticks} tick(s)."
    )
    sender.send_message("\n".join(lines))
    return True


def _teleport_to_rank(self: "OnistoneEssentials", sender: CommandSender, rank: int) -> bool:
    if not isinstance(sender, Player):
        sender.send_message("§cOnly a player can teleport to a hotspot.")
        return False
    if not _require_permission(sender, TELEPORT_PERMISSION):
        return False
    settings = self.entity_hotspot_service.settings()
    if not settings.teleport_enabled:
        sender.send_message("§cHotspot teleporting is disabled in config.json.")
        return False

    owner_key = self.entity_hotspot_service.sender_key(sender)
    try:
        snapshot, _selection, result = self.entity_hotspot_service.get_rank(owner_key, rank)
    except (LookupError, TimeoutError, IndexError) as exc:
        sender.send_message(f"§c{exc}")
        return False

    safe = find_safe_inspection_position(
        self.server.level,
        result.dimension_key,
        result.dimension_name,
        result.representative_x,
        result.representative_y,
        result.representative_z,
        settings.teleport_horizontal_radius,
        settings.teleport_vertical_radius,
        settings.teleport_max_candidates,
    )
    if not safe.success:
        sender.send_message(
            f"§cCannot teleport to #{rank} from scan {snapshot.scan_id}: {safe.reason}. "
            f"No chunks were loaded by this check."
        )
        return False
    try:
        current = sender.location
        destination = Location(
            safe.dimension,
            safe.x,
            safe.y,
            safe.z,
            current.pitch,
            current.yaw,
        )
        teleported = sender.teleport(destination)
    except Exception as exc:
        sender.send_message(f"§cTeleport failed without moving you: {exc}")
        return False
    if not teleported:
        sender.send_message("§cEndstone rejected the teleport; you were not moved.")
        return False
    sender.send_message(
        f"§aTeleported near hotspot #{rank} in {result.dimension_name} at "
        f"{safe.x:.1f}, {safe.y:.1f}, {safe.z:.1f}."
    )
    return True


def _show_hotspot_help(sender: CommandSender) -> bool:
    sender.send_message(
        "§eEntity hotspot commands\n"
        "§f/entityinfo hotspots [page] §7- busiest loaded chunks\n"
        "§f/entityinfo hotspots chunks [page] §7- select chunk ranking\n"
        "§f/entityinfo hotspots groups [page] §7- connected 8-neighbor dense chunks\n"
        "§f/entityinfo hotspots filter <chunks|groups> <dimension|all> "
        "<all|mobs|items|other|namespace:id> [page]\n"
        "§f/entityinfo hotspots detail <rank> §7- saved-result breakdown\n"
        "§f/entityinfo hotspots refresh §7- rescan the selected query\n"
        "§f/entityinfo tp <rank> §7- player-only validated teleport\n"
        "§6Only currently loaded actors are sampled. Players are excluded by default. "
        "Named, tamed, and custom actors are otherwise not excluded. Item stacks count as one entity.\n"
        "§7Multi-tick scans are a sampling window, not an atomic world snapshot. Pages, details, and "
        "teleports reuse your immutable saved scan and never silently rescan."
    )
    return True


def _handle_hotspots(
    self: "OnistoneEssentials", sender: CommandSender, args: list[str]
) -> bool:
    if not _require_permission(sender, HOTSPOT_PERMISSION):
        return False
    default_filter = HotspotFilter.create()
    if len(args) == 1:
        return _reuse_or_scan(self, sender, "chunks", default_filter, 1)

    action = args[1].lower()
    if action == "help":
        return _show_hotspot_help(sender)
    if action == "detail":
        if len(args) != 3:
            sender.send_message("§cUsage: /entityinfo hotspots detail <rank>")
            return False
        rank = _safe_int(args[2], "Rank", sender)
        return False if rank is None else _show_detail(self, sender, rank)
    if action == "refresh":
        if len(args) != 2:
            sender.send_message("§cUsage: /entityinfo hotspots refresh")
            return False
        owner_key = self.entity_hotspot_service.sender_key(sender)
        try:
            snapshot, selection = self.entity_hotspot_service.get_refresh_query(owner_key)
            return _begin_scan(self, sender, selection.mode, snapshot.filters, 1)
        except LookupError:
            return _begin_scan(self, sender, "chunks", default_filter, 1)
    if action in ("chunks", "groups"):
        if len(args) > 3:
            sender.send_message(f"§cUsage: /entityinfo hotspots {action} [page]")
            return False
        page = 1 if len(args) == 2 else _safe_int(args[2], "Page", sender)
        if page is None:
            return False
        owner_key = self.entity_hotspot_service.sender_key(sender)
        try:
            self.entity_hotspot_service.get_selected(owner_key)
        except TimeoutError as exc:
            sender.send_message(f"§c{exc}")
            return False
        except LookupError as exc:
            if len(args) == 2:
                return _begin_scan(self, sender, action, default_filter, page)
            sender.send_message(f"§c{exc}")
            return False
        return _view_selected(self, sender, action, page)
    if action == "filter":
        if len(args) not in (5, 6):
            sender.send_message(
                "§cUsage: /entityinfo hotspots filter <chunks|groups> <dimension> "
                "<all|mobs|items|other|namespace:id> [page]"
            )
            return False
        mode = args[2].lower()
        if mode not in ("chunks", "groups"):
            sender.send_message("§cFilter mode must be chunks or groups.")
            return False
        try:
            filters = HotspotFilter.create(args[3], args[4])
        except ValueError as exc:
            sender.send_message(f"§c{exc}")
            return False
        page = 1 if len(args) == 5 else _safe_int(args[5], "Page", sender)
        if page is None:
            return False
        return _reuse_or_scan(self, sender, mode, filters, page)

    if len(args) == 2:
        page = _safe_int(action, "Page", sender)
        if page is not None:
            owner_key = self.entity_hotspot_service.sender_key(sender)
            try:
                self.entity_hotspot_service.get_selected(owner_key)
            except (LookupError, TimeoutError) as exc:
                sender.send_message(f"§c{exc}")
                return False
            return _view_selected(self, sender, "chunks", page)
    sender.send_message("§cUnknown hotspot action. Use /entityinfo hotspots help.")
    return False


def _handle_list(self: "OnistoneEssentials", sender: CommandSender, args: list[str]) -> bool:
    if len(args) > 2:
        sender.send_message("§cUsage: /entityinfo list [page]")
        return False
    page = 1 if len(args) == 1 else _safe_int(args[1], "Page", sender)
    if page is None:
        return False
    try:
        actors = self.server.level.actors
    except Exception as exc:
        sender.send_message(f"§cCould not enumerate loaded actors: {exc}")
        return False
    type_counts: Counter[str] = Counter()
    skipped = 0
    for actor in actors:
        try:
            type_counts[str(actor.type)] += 1
        except Exception:
            skipped += 1
    sorted_types = sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))
    total_pages = max(1, math.ceil(len(sorted_types) / 10))
    if page > total_pages:
        sender.send_message(f"§cPage must be between 1 and {total_pages}.")
        return False
    page_items = sorted_types[(page - 1) * 10 : page * 10]
    sender.send_message(
        f"§eEntity Summary §7(Page {page}/{total_pages})\n"
        f"§eTotal exposed loaded actors: §f{len(actors)} §7| inaccessible: §f{skipped}"
    )
    for entity_type, count in page_items:
        sender.send_message(f"  §7- §e{entity_type}: §f{count}")
    return True


def _handle_target(sender: CommandSender) -> bool:
    if not isinstance(sender, Player):
        sender.send_message("§cTargeted entity inspection can only be executed by a player.")
        return False
    actor = get_target_entity(sender)
    if actor is None:
        sender.send_message("§cNo entities found 10 blocks in front of you.")
        return False
    health = f"{actor.health}/{actor.max_health}" if isinstance(actor, Mob) else "N/A"
    sender.send_message(
        f"§bEntity Information:\n"
        f"§7- §eName: §f\"{getattr(actor, 'name_tag', None) or 'Unset'}\"\n"
        f"§7- §eType: §f{actor.type}\n"
        f"§7- §eUnique ID: §f{actor.id}\n"
        f"§7- §eRuntime ID: §f{actor.runtime_id}\n"
        f"§7- §eLocation: §fx: {actor.location.block_x} §7/ §fy: "
        f"{actor.location.block_y} §7/ §fz: {actor.location.block_z}\n"
        f"§7- §eRotation: §fyaw: {round(actor.location.yaw, 2)} §7/ §fpitch: "
        f"{round(actor.location.pitch, 2)}\n"
        f"§7- §eDimension: §f{actor.dimension.name}\n"
        f"§7- §eHealth: §f{health}\n"
        f"§7- §eGrounded: §f{actor.is_on_ground}\n"
        f"§7- §eIn Lava: §f{actor.is_in_lava}\n"
        f"§7- §eIn Water: §f{actor.is_in_water}\n"
        f"§7- §eTags: §f{actor.scoreboard_tags}"
    )
    return True


def handler(self: "OnistoneEssentials", sender: CommandSender, args: list[str]) -> bool:
    if BlockCommandSender is not None and isinstance(sender, BlockCommandSender):
        sender.send_message("§cThis command cannot be automated by a command block.")
        return False
    if any("@" in arg for arg in args):
        sender.send_message("§cTarget selectors are invalid for this command.")
        return False
    if not args:
        return _handle_target(sender)

    action = args[0].lower()
    if action == "list":
        return _handle_list(self, sender, args)
    if action == "hotspots":
        return _handle_hotspots(self, sender, args)
    if action == "tp":
        if len(args) != 2:
            sender.send_message("§cUsage: /entityinfo tp <rank>")
            return False
        rank = _safe_int(args[1], "Rank", sender)
        return False if rank is None else _teleport_to_rank(self, sender, rank)

    sender.send_message("§cUnknown action. Use /entityinfo hotspots help.")
    return False
