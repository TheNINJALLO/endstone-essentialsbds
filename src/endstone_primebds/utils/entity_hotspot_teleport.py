"""Conservative, loaded-chunk-only inspection-position validation."""

from __future__ import annotations

from dataclasses import dataclass
import math

from endstone_primebds.utils.entity_hotspots import canonical_dimension, chunk_coordinates


AIR_BLOCKS = frozenset(
    {"minecraft:air", "minecraft:cave_air", "minecraft:void_air", "air", "cave_air", "void_air"}
)
HAZARDOUS_BLOCK_PARTS = (
    "lava",
    "fire",
    "cactus",
    "magma",
    "campfire",
    "sweet_berry_bush",
    "powder_snow",
    "portal",
    "end_gateway",
)
UNSUPPORTED_FLOOR_PARTS = (
    "water",
    "air",
    "flower",
    "sapling",
    "mushroom",
    "fungus",
    "roots",
    "short_grass",
    "tallgrass",
    "fern",
    "crop",
    "wheat",
    "carrot",
    "potato",
    "beetroot",
    "torch",
    "rail",
    "carpet",
    "sign",
    "banner",
    "button",
    "pressure_plate",
    "tripwire",
    "vine",
    "lichen",
    "ladder",
    "scaffolding",
    "snow_layer",
    "seagrass",
    "kelp",
    "reeds",
    "sugar_cane",
    "trapdoor",
    "fence",
    "wall",
)


@dataclass(frozen=True, slots=True)
class SafePositionResult:
    success: bool
    dimension: object | None = None
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    reason: str = ""
    checked_candidates: int = 0


def _dimension_matches(dimension, key: str, name: str) -> bool:
    actual_name = str(getattr(dimension, "name", ""))
    actual = canonical_dimension(actual_name)
    return actual in {canonical_dimension(key), canonical_dimension(name)}


def resolve_loaded_dimension(level, key: str, name: str):
    """Resolve only from the level's currently exposed dimensions."""

    try:
        dimensions = list(level.dimensions)
    except Exception:
        return None
    for dimension in dimensions:
        if _dimension_matches(dimension, key, name):
            return dimension
    return None


def _standing_height_bounds(dimension_name: str, center_y: int, radius: int) -> tuple[int, int]:
    canonical = canonical_dimension(dimension_name)
    if canonical == "overworld":
        return max(-63, center_y - radius), min(318, center_y + radius)
    if canonical == "nether":
        # A standing Y above 124 risks the inaccessible Nether roof area.
        return max(1, center_y - radius), min(124, center_y + radius)
    if canonical == "the_end":
        return max(1, center_y - radius), min(254, center_y + radius)
    return max(-2047, center_y - radius), min(2046, center_y + radius)


def _horizontal_offsets(radius: int) -> list[tuple[int, int]]:
    offsets = [
        (offset_x, offset_z)
        for offset_x in range(-radius, radius + 1)
        for offset_z in range(-radius, radius + 1)
    ]
    offsets.sort(
        key=lambda offset: (
            offset[0] * offset[0] + offset[1] * offset[1],
            abs(offset[0]) + abs(offset[1]),
            offset[0],
            offset[1],
        )
    )
    return offsets


def _vertical_candidates(center: int, lower: int, upper: int) -> list[int]:
    values = []
    max_offset = max(center - lower, upper - center)
    for offset in range(max_offset + 1):
        above = center + offset
        below = center - offset
        if lower <= above <= upper:
            values.append(above)
        if offset and lower <= below <= upper:
            values.append(below)
    return values


def _is_air(block_type: str) -> bool:
    return block_type.lower() in AIR_BLOCKS


def _contains_any(block_type: str, parts: tuple[str, ...]) -> bool:
    normalized = block_type.lower()
    return any(part in normalized for part in parts)


def _is_safe_triplet(floor_type: str, feet_type: str, head_type: str) -> bool:
    if not _is_air(feet_type) or not _is_air(head_type):
        return False
    if _contains_any(floor_type, HAZARDOUS_BLOCK_PARTS):
        return False
    if _contains_any(floor_type, UNSUPPORTED_FLOOR_PARTS):
        return False
    return True


def find_safe_inspection_position(
    level,
    dimension_key: str,
    dimension_name: str,
    representative_x: float,
    representative_y: float,
    representative_z: float,
    horizontal_radius: int,
    vertical_radius: int,
    max_candidates: int,
) -> SafePositionResult:
    """Find a conservative standing position without loading destination chunks.

    Endstone 0.11.9 does not expose a generic block collision/passability property.
    This routine therefore accepts only two blocks of explicit air above a floor
    that is not in a conservative non-support/hazard denylist.
    """

    dimension = resolve_loaded_dimension(level, dimension_key, dimension_name)
    coordinates = (
        f"{math.floor(representative_x)}, {math.floor(representative_y)}, "
        f"{math.floor(representative_z)}"
    )
    if dimension is None:
        return SafePositionResult(False, reason=f"dimension is unavailable near {coordinates}")

    try:
        loaded_chunks = {(int(chunk.x), int(chunk.z)) for chunk in dimension.loaded_chunks}
    except Exception:
        return SafePositionResult(
            False, reason=f"loaded chunks could not be verified near {coordinates}"
        )
    target_chunk = chunk_coordinates(representative_x, representative_z)
    if target_chunk not in loaded_chunks:
        return SafePositionResult(
            False, reason=f"hotspot chunk {target_chunk[0]}, {target_chunk[1]} is no longer loaded"
        )

    center_x = math.floor(representative_x)
    center_y = math.floor(representative_y)
    center_z = math.floor(representative_z)
    horizontal_radius = max(0, int(horizontal_radius))
    vertical_radius = max(2, int(vertical_radius))
    max_candidates = max(1, int(max_candidates))
    lower, upper = _standing_height_bounds(dimension_name, center_y, vertical_radius)
    if lower > upper:
        return SafePositionResult(False, reason=f"Y range is unsafe near {coordinates}")

    horizontal = _horizontal_offsets(horizontal_radius)
    vertical = _vertical_candidates(center_y, lower, upper)
    checked = 0

    # Round-robin by vertical distance avoids spending the entire budget on one
    # column while still preferring the sampled hotspot height.
    for standing_y in vertical:
        for offset_x, offset_z in horizontal:
            block_x = center_x + offset_x
            block_z = center_z + offset_z
            if chunk_coordinates(block_x, block_z) not in loaded_chunks:
                continue
            if checked >= max_candidates:
                return SafePositionResult(
                    False,
                    reason=f"no safe position verified near {coordinates} before the search limit",
                    checked_candidates=checked,
                )
            checked += 1
            try:
                floor_type = str(dimension.get_block_at(block_x, standing_y - 1, block_z).type)
                feet_type = str(dimension.get_block_at(block_x, standing_y, block_z).type)
                head_type = str(dimension.get_block_at(block_x, standing_y + 1, block_z).type)
            except Exception:
                continue
            if not _is_safe_triplet(floor_type, feet_type, head_type):
                continue

            # Reject obvious adjacent contact hazards at body height.
            try:
                adjacent = [
                    str(dimension.get_block_at(block_x + dx, standing_y, block_z + dz).type)
                    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if chunk_coordinates(block_x + dx, block_z + dz) in loaded_chunks
                ]
            except Exception:
                continue
            if any(_contains_any(block_type, HAZARDOUS_BLOCK_PARTS) for block_type in adjacent):
                continue
            return SafePositionResult(
                True,
                dimension=dimension,
                x=block_x + 0.5,
                y=float(standing_y),
                z=block_z + 0.5,
                checked_candidates=checked,
            )

    return SafePositionResult(
        False,
        reason=f"no conservative safe standing position was found near {coordinates}",
        checked_candidates=checked,
    )
