from __future__ import annotations

from conftest import SRC_PACKAGE, load_source


teleport_module = load_source(
    "endstone_primebds.utils.entity_hotspot_teleport",
    SRC_PACKAGE / "utils" / "entity_hotspot_teleport.py",
)
find_safe_inspection_position = teleport_module.find_safe_inspection_position


class Chunk:
    def __init__(self, x, z):
        self.x = x
        self.z = z


class Block:
    def __init__(self, block_type):
        self.type = block_type


class Dimension:
    def __init__(self, name, loaded, block_type):
        self.name = name
        self.loaded_chunks = [Chunk(*coordinates) for coordinates in loaded]
        self.block_type = block_type
        self.block_reads = 0

    def get_block_at(self, x, y, z):
        self.block_reads += 1
        return Block(self.block_type(x, y, z))


class Level:
    def __init__(self, dimensions):
        self.dimensions = dimensions


def safe_column(_x, y, _z):
    return "minecraft:stone" if y == 63 else "minecraft:air"


def test_safe_search_selects_the_snapshot_dimension():
    overworld = Dimension("Overworld", {(0, 0)}, safe_column)
    nether = Dimension("Nether", {(0, 0)}, safe_column)
    result = find_safe_inspection_position(
        Level([overworld, nether]),
        "nether",
        "Nether",
        1,
        64,
        1,
        0,
        4,
        20,
    )

    assert result.success is True
    assert result.dimension is nether
    assert (result.x, result.y, result.z) == (1.5, 64.0, 1.5)
    assert overworld.block_reads == 0


def test_unloaded_hotspot_is_rejected_before_any_block_access():
    dimension = Dimension("Overworld", set(), safe_column)
    result = find_safe_inspection_position(
        Level([dimension]),
        "overworld",
        "Overworld",
        1,
        64,
        1,
        2,
        4,
        20,
    )

    assert result.success is False
    assert "no longer loaded" in result.reason
    assert dimension.block_reads == 0


def test_hazardous_or_unverifiable_position_is_refused():
    dimension = Dimension("Overworld", {(0, 0)}, lambda _x, _y, _z: "minecraft:lava")
    result = find_safe_inspection_position(
        Level([dimension]),
        "overworld",
        "Overworld",
        1,
        64,
        1,
        0,
        2,
        8,
    )

    assert result.success is False
    assert "safe" in result.reason
    assert result.checked_candidates <= 8


def test_missing_dimension_is_rejected_without_substitution():
    overworld = Dimension("Overworld", {(0, 0)}, safe_column)
    result = find_safe_inspection_position(
        Level([overworld]),
        "my_pack:moon",
        "my_pack:moon",
        1,
        64,
        1,
        0,
        2,
        8,
    )

    assert result.success is False
    assert "dimension is unavailable" in result.reason
    assert overworld.block_reads == 0

