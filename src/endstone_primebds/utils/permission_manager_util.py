"""Pure helpers shared by the Onistone permissions manager and its tests."""

from __future__ import annotations

import re
from collections import defaultdict


COLOR_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Black", "§0"),
    ("Dark Blue", "§1"),
    ("Dark Green", "§2"),
    ("Dark Aqua", "§3"),
    ("Dark Red", "§4"),
    ("Dark Purple", "§5"),
    ("Gold", "§6"),
    ("Gray", "§7"),
    ("Dark Gray", "§8"),
    ("Blue", "§9"),
    ("Green", "§a"),
    ("Aqua", "§b"),
    ("Red", "§c"),
    ("Light Purple", "§d"),
    ("Yellow", "§e"),
    ("White", "§f"),
    ("Minecoin Gold", "§g"),
)

PERMISSION_STATES: tuple[str, ...] = ("Inherit / neutral", "Allow", "Deny")


def migrate_permission_name(permission: str) -> str:
    """Return the Onistone namespace for a legacy Essentials permission."""
    lowered = permission.lower()
    legacy_prefix = "".join(("prime", "bds."))
    if lowered.startswith(legacy_prefix):
        return "onistone." + permission[len(legacy_prefix) :]
    return permission


def migrate_permission_mapping(permissions: dict[str, bool]) -> tuple[dict[str, bool], bool]:
    """Migrate permission keys without overwriting an explicitly new key."""
    migrated: dict[str, bool] = {}
    changed = False

    # Preserve already migrated values when both forms happen to exist.
    for permission, value in permissions.items():
        new_name = migrate_permission_name(str(permission))
        if new_name == permission:
            migrated[new_name] = bool(value)

    for permission, value in permissions.items():
        new_name = migrate_permission_name(str(permission))
        changed = changed or new_name != permission
        migrated.setdefault(new_name, bool(value))

    return migrated, changed


def permission_groups(permissions: list[str] | set[str] | tuple[str, ...]) -> dict[str, list[str]]:
    """Group unique permissions by their first namespace component."""
    grouped: defaultdict[str, set[str]] = defaultdict(set)
    for permission in permissions:
        normalized = migrate_permission_name(str(permission)).strip().lower()
        if not normalized:
            continue
        grouped[normalized.split(".", 1)[0]].add(normalized)
    return {group: sorted(values) for group, values in sorted(grouped.items())}


def permission_state_index(permissions: dict[str, bool], permission: str) -> int:
    """Return the dropdown index for neutral, allow, or deny."""
    lookup = {str(key).lower(): bool(value) for key, value in permissions.items()}
    key = permission.lower()
    if key not in lookup:
        return 0
    return 1 if lookup[key] else 2


def set_permission_state(
    permissions: dict[str, bool], permission: str, state_index: int
) -> dict[str, bool]:
    """Apply a GUI state choice to a copy of an explicit permission mapping."""
    updated = {str(key).lower(): bool(value) for key, value in permissions.items()}
    key = migrate_permission_name(permission.strip()).lower()
    if not key:
        raise ValueError("Permission cannot be empty")
    if state_index == 0:
        updated.pop(key, None)
    elif state_index == 1:
        updated[key] = True
    elif state_index == 2:
        updated[key] = False
    else:
        raise ValueError("Invalid permission state")
    return updated


def color_index(color_code: str) -> int:
    """Return a safe dropdown index for a Minecraft color code."""
    normalized = str(color_code).replace("Â§", "§").lower()
    for index, (_, code) in enumerate(COLOR_OPTIONS):
        if code.lower() == normalized:
            return index
    return 7  # Gray


def infer_display_name(rank_name: str, group: dict) -> str:
    """Read the saved title or recover it from an older formatted prefix."""
    saved = str(group.get("display_name", "")).strip()
    if saved:
        return saved

    prefix = str(group.get("prefix", "")).replace("Â§", "§")
    bracket_match = re.search(r"\[(?:§[0-9a-gk-or])*([^\]§]+)", prefix, re.IGNORECASE)
    if bracket_match:
        return bracket_match.group(1).strip()
    return rank_name


def infer_color(group: dict) -> str:
    """Read a saved color or recover the title color from an older prefix."""
    saved = str(group.get("color", "")).replace("Â§", "§")
    if any(saved.lower() == code.lower() for _, code in COLOR_OPTIONS):
        return saved

    prefix = str(group.get("prefix", "")).replace("Â§", "§")
    bracket_match = re.search(r"\[\s*(§[0-9a-g])", prefix, re.IGNORECASE)
    if bracket_match:
        return bracket_match.group(1).lower()
    return "§7"


def build_rank_prefix(
    display_name: str,
    color_code: str,
    show_title: bool = True,
    brackets: bool = True,
) -> str:
    """Build the chat/name-tag prefix controlled by the rank settings GUI."""
    title = display_name.strip()
    if not show_title or not title:
        return ""
    color = COLOR_OPTIONS[color_index(color_code)][1]
    if brackets:
        return f"§8[{color}{title}§8] {color}"
    return f"{color}{title} §r{color}"


def apply_rank_appearance(
    group: dict,
    display_name: str,
    color_code: str,
    show_title: bool,
    brackets: bool,
    suffix: str,
) -> dict:
    """Return rank data with consistent editable title metadata and prefix."""
    updated = dict(group)
    title = display_name.strip()
    if not title:
        raise ValueError("Rank title cannot be empty")
    color = COLOR_OPTIONS[color_index(color_code)][1]
    updated.update(
        {
            "display_name": title,
            "color": color,
            "show_title": bool(show_title),
            "brackets": bool(brackets),
            "prefix": build_rank_prefix(title, color, show_title, brackets),
            "suffix": suffix,
        }
    )
    return updated
