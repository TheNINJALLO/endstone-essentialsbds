from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "endstone_primebds"
    / "utils"
    / "permission_manager_util.py"
)
SPEC = importlib.util.spec_from_file_location("permission_manager_util", MODULE_PATH)
permission_manager = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(permission_manager)


def test_legacy_permission_namespace_migrates_without_overwriting_new_value():
    migrated, changed = permission_manager.migrate_permission_mapping(
        {
            "primebds.command.rank": False,
            "onistone.command.rank": True,
            "minecraft.command.list": True,
        }
    )

    assert changed is True
    assert migrated == {
        "onistone.command.rank": True,
        "minecraft.command.list": True,
    }


def test_permissions_are_grouped_and_sorted_for_category_forms():
    grouped = permission_manager.permission_groups(
        [
            "minecraft.command.tell",
            "Onistone.Command.Rank",
            "primebds.command.permissions",
            "minecraft.command.list",
        ]
    )

    assert grouped == {
        "minecraft": ["minecraft.command.list", "minecraft.command.tell"],
        "onistone": ["onistone.command.permissions", "onistone.command.rank"],
    }


def test_permission_state_supports_allow_deny_and_inherit():
    explicit = {}
    explicit = permission_manager.set_permission_state(
        explicit, "onistone.command.rank", 1
    )
    assert explicit["onistone.command.rank"] is True
    assert permission_manager.permission_state_index(
        explicit, "onistone.command.rank"
    ) == 1

    explicit = permission_manager.set_permission_state(
        explicit, "onistone.command.rank", 2
    )
    assert explicit["onistone.command.rank"] is False
    assert permission_manager.permission_state_index(
        explicit, "onistone.command.rank"
    ) == 2

    explicit = permission_manager.set_permission_state(
        explicit, "onistone.command.rank", 0
    )
    assert "onistone.command.rank" not in explicit


def test_rank_appearance_builds_editable_title_and_color_prefix():
    updated = permission_manager.apply_rank_appearance(
        {"permissions": {"*": True}, "inherits": ["Default"]},
        "Owner",
        "§d",
        True,
        True,
        "§r",
    )

    assert updated["display_name"] == "Owner"
    assert updated["color"] == "§d"
    assert updated["prefix"] == "§8[§dOwner§8] §d"
    assert updated["suffix"] == "§r"
    assert updated["permissions"] == {"*": True}


def test_existing_admin_prefix_is_read_for_upgrade_compatibility():
    group = {"prefix": "§8[§cAdmin§8] §c"}

    assert permission_manager.infer_display_name("Operator", group) == "Admin"
    assert permission_manager.infer_color(group) == "§c"
