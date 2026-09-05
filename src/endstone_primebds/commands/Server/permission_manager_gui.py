"""Bedrock form-based administration for Onistone ranks and permissions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from endstone import Player

from endstone_primebds.utils.config_util import load_permissions, save_permissions
from endstone_primebds.utils.form_wrapper_util import (
    ActionFormData,
    ActionFormResponse,
    ModalFormData,
    ModalFormResponse,
)
import endstone_primebds.utils.internal_permissions_util as perms_util
from endstone_primebds.utils.permission_manager_util import (
    COLOR_OPTIONS,
    PERMISSION_STATES,
    apply_rank_appearance,
    color_index,
    infer_color,
    infer_display_name,
    migrate_permission_name,
    permission_groups,
    permission_state_index,
    set_permission_state,
)

if TYPE_CHECKING:
    from endstone_primebds.primebds import OnistoneEssentials


def _show(form, player: Player, callback) -> None:
    form.show(player).then(callback)


def _rank_key(ranks: dict, requested: str) -> str | None:
    return next((name for name in ranks if name.lower() == requested.lower()), None)


def _refresh_rank_players(plugin: "OnistoneEssentials", affected_rank: str) -> None:
    perms_util.reload_rank_list()
    perms_util.clear_prefix_suffix_cache()
    for target in plugin.server.online_players:
        user = plugin.db.get_online_user(target.xuid)
        if user and user.internal_rank.lower() == affected_rank.lower():
            plugin.reload_custom_perms(target)
            perms_util.invalidate_perm_cache(target.xuid)


def _all_permissions(explicit: dict[str, bool] | None = None) -> list[str]:
    values = set(perms_util.MANAGED_PERMISSIONS_LIST)
    if explicit:
        values.update(explicit)
    return sorted(migrate_permission_name(value).lower() for value in values)


def open_permissions_manager(plugin: "OnistoneEssentials", player: Player) -> None:
    form = ActionFormData()
    form.title("Onistone Permissions")
    form.body(
        "Configure ranks without editing JSON. Changes are saved immediately and "
        "applied to online players."
    )
    form.button("Manage rank sets")
    form.button("Manage player overrides")
    form.button("Create a rank set")
    form.button("Close")

    def submit(admin: Player, response: ActionFormResponse) -> None:
        if response.canceled:
            return
        selection = int(response.selection)
        if selection == 0:
            _show_rank_list(plugin, admin)
        elif selection == 1:
            _show_online_player_list(plugin, admin)
        elif selection == 2:
            _show_create_rank(plugin, admin)

    _show(form, player, submit)


def _show_rank_list(plugin: "OnistoneEssentials", player: Player) -> None:
    ranks = load_permissions(cache=False)
    rank_names = list(ranks)
    form = ActionFormData()
    form.title("Onistone Rank Sets")
    form.body("Choose the rank set you want to configure.")
    for rank_name in rank_names:
        group = ranks[rank_name]
        title = infer_display_name(rank_name, group)
        form.button(f"{infer_color(group)}{title}§r\n§8Internal: {rank_name}")
    form.button("Back")

    def submit(admin: Player, response: ActionFormResponse) -> None:
        if response.canceled:
            return
        selection = int(response.selection)
        if selection == len(rank_names):
            open_permissions_manager(plugin, admin)
        elif 0 <= selection < len(rank_names):
            _show_rank_menu(plugin, admin, rank_names[selection])

    _show(form, player, submit)


def _show_rank_menu(
    plugin: "OnistoneEssentials", player: Player, rank_name: str
) -> None:
    ranks = load_permissions(cache=False)
    actual_rank = _rank_key(ranks, rank_name)
    if actual_rank is None:
        player.send_message("§cThat rank no longer exists.")
        _show_rank_list(plugin, player)
        return

    group = ranks[actual_rank]
    title = infer_display_name(actual_rank, group)
    explicit = group.get("permissions", {})
    parent_text = ", ".join(group.get("inherits", [])) or "None"
    form = ActionFormData()
    form.title(f"Rank: {title}")
    form.body(
        f"Internal name: §f{actual_rank}§r\n"
        f"Explicit permissions: §f{len(explicit)}§r\n"
        f"Parent: §f{parent_text}§r\n"
        f"Weight: §f{group.get('weight', 0)}"
    )
    form.button("Edit permissions")
    form.button("Edit title, color & settings")
    form.button("Assign to an online player")
    form.button("Back")

    def submit(admin: Player, response: ActionFormResponse) -> None:
        if response.canceled:
            return
        selection = int(response.selection)
        if selection == 0:
            _show_rank_categories(plugin, admin, actual_rank)
        elif selection == 1:
            _show_rank_settings(plugin, admin, actual_rank)
        elif selection == 2:
            _show_rank_assignment(plugin, admin, actual_rank)
        elif selection == 3:
            _show_rank_list(plugin, admin)

    _show(form, player, submit)


def _show_rank_categories(
    plugin: "OnistoneEssentials", player: Player, rank_name: str
) -> None:
    ranks = load_permissions(cache=False)
    actual_rank = _rank_key(ranks, rank_name)
    if actual_rank is None:
        _show_rank_list(plugin, player)
        return
    explicit = ranks[actual_rank].get("permissions", {})
    grouped = permission_groups(_all_permissions(explicit))
    categories = list(grouped)

    form = ActionFormData()
    form.title(f"{actual_rank}: Permissions")
    form.body(
        "Choose a plugin/category, then select a permission and set it to Allow, "
        "Deny, or Inherit."
    )
    for category in categories:
        form.button(f"{category}\n§8{len(grouped[category])} permissions")
    form.button("Custom permission")
    form.button("Back")

    def submit(admin: Player, response: ActionFormResponse) -> None:
        if response.canceled:
            return
        selection = int(response.selection)
        if selection < len(categories):
            category = categories[selection]
            _show_rank_permission_editor(
                plugin, admin, actual_rank, category, grouped[category]
            )
        elif selection == len(categories):
            _show_custom_rank_permission(plugin, admin, actual_rank)
        else:
            _show_rank_menu(plugin, admin, actual_rank)

    _show(form, player, submit)


def _show_rank_permission_editor(
    plugin: "OnistoneEssentials",
    player: Player,
    rank_name: str,
    category: str,
    permissions: list[str],
) -> None:
    ranks = load_permissions(cache=False)
    actual_rank = _rank_key(ranks, rank_name)
    if actual_rank is None or not permissions:
        _show_rank_categories(plugin, player, rank_name)
        return
    explicit = ranks[actual_rank].get("permissions", {})
    labels = []
    for permission in permissions:
        state = permission_state_index(explicit, permission)
        marker = ("§7Inherit", "§aAllow", "§cDeny")[state]
        labels.append(f"{permission} — {marker}")

    form = ModalFormData()
    form.title(f"{actual_rank}: {category}")
    form.dropdown("Permission", labels)
    form.dropdown("New state", list(PERMISSION_STATES))
    form.submit_button("Save permission")

    def submit(admin: Player, response: ModalFormResponse) -> None:
        if response.canceled:
            _show_rank_categories(plugin, admin, actual_rank)
            return
        permission_index = int(response.formValues[0])
        state_index = int(response.formValues[1])
        if permission_index < 0 or permission_index >= len(permissions):
            admin.send_message("§cInvalid permission selection.")
            return
        permission = permissions[permission_index]
        latest = load_permissions(cache=False)
        latest_rank = _rank_key(latest, actual_rank)
        if latest_rank is None:
            admin.send_message("§cThat rank no longer exists.")
            return
        current = latest[latest_rank].get("permissions", {})
        latest[latest_rank]["permissions"] = set_permission_state(
            current, permission, state_index
        )
        save_permissions(latest, True)
        _refresh_rank_players(plugin, latest_rank)
        admin.send_message(
            f"§aSaved §f{permission}§a as §f{PERMISSION_STATES[state_index]}§a "
            f"for §f{latest_rank}§a."
        )
        _show_rank_categories(plugin, admin, latest_rank)

    _show(form, player, submit)


def _show_custom_rank_permission(
    plugin: "OnistoneEssentials", player: Player, rank_name: str
) -> None:
    form = ModalFormData()
    form.title(f"{rank_name}: Custom Permission")
    form.text_field("Permission node", "plugin.command.example")
    form.dropdown("State", list(PERMISSION_STATES))
    form.submit_button("Save permission")

    def submit(admin: Player, response: ModalFormResponse) -> None:
        if response.canceled:
            _show_rank_categories(plugin, admin, rank_name)
            return
        permission = migrate_permission_name(str(response.formValues[0]).strip()).lower()
        state_index = int(response.formValues[1])
        try:
            ranks = load_permissions(cache=False)
            actual_rank = _rank_key(ranks, rank_name)
            if actual_rank is None:
                raise ValueError("Rank no longer exists")
            ranks[actual_rank]["permissions"] = set_permission_state(
                ranks[actual_rank].get("permissions", {}), permission, state_index
            )
            save_permissions(ranks, True)
            _refresh_rank_players(plugin, actual_rank)
            admin.send_message(f"§aSaved §f{permission}§a for §f{actual_rank}§a.")
            _show_rank_categories(plugin, admin, actual_rank)
        except ValueError as error:
            admin.send_message(f"§c{error}")

    _show(form, player, submit)


def _show_rank_settings(
    plugin: "OnistoneEssentials", player: Player, rank_name: str
) -> None:
    ranks = load_permissions(cache=False)
    actual_rank = _rank_key(ranks, rank_name)
    if actual_rank is None:
        _show_rank_list(plugin, player)
        return
    group = ranks[actual_rank]
    title = infer_display_name(actual_rank, group)
    color = infer_color(group)
    parents = ["None"] + [name for name in ranks if name != actual_rank]
    existing_parents = group.get("inherits", [])
    parent_index = 0
    if existing_parents and existing_parents[0] in parents:
        parent_index = parents.index(existing_parents[0])

    form = ModalFormData()
    form.title(f"{actual_rank}: Rank Settings")
    form.text_field("Displayed title", "Admin, Moderator, Member...", title)
    form.dropdown(
        "Title color", [name for name, _ in COLOR_OPTIONS], color_index(color)
    )
    form.toggle("Show title in chat/name tag", group.get("show_title", bool(group.get("prefix"))))
    form.toggle("Put title in brackets", group.get("brackets", True))
    form.dropdown("Parent rank", parents, parent_index)
    form.text_field("Weight", "0", str(group.get("weight", 0)))
    form.text_field("Suffix (optional)", "Formatting after the player name", str(group.get("suffix", "§r")))
    form.submit_button("Save rank settings")

    def submit(admin: Player, response: ModalFormResponse) -> None:
        if response.canceled:
            _show_rank_menu(plugin, admin, actual_rank)
            return
        values = response.formValues
        try:
            new_title = str(values[0]).strip()
            selected_color = COLOR_OPTIONS[int(values[1])][1]
            show_title = bool(values[2])
            brackets = bool(values[3])
            selected_parent = parents[int(values[4])]
            weight = int(str(values[5]).strip())
            suffix = str(values[6])
            latest = load_permissions(cache=False)
            latest_rank = _rank_key(latest, actual_rank)
            if latest_rank is None:
                raise ValueError("Rank no longer exists")
            updated = apply_rank_appearance(
                latest[latest_rank],
                new_title,
                selected_color,
                show_title,
                brackets,
                suffix,
            )
            updated["inherits"] = [] if selected_parent == "None" else [selected_parent]
            updated["weight"] = weight
            latest[latest_rank] = updated
            save_permissions(latest, True)
            _refresh_rank_players(plugin, latest_rank)
            admin.send_message(
                f"§aUpdated §f{latest_rank}§a to display as "
                f"{selected_color}{new_title}§a."
            )
            _show_rank_menu(plugin, admin, latest_rank)
        except (ValueError, IndexError) as error:
            admin.send_message(f"§cCould not save rank settings: {error}")

    _show(form, player, submit)


def _show_create_rank(plugin: "OnistoneEssentials", player: Player) -> None:
    ranks = load_permissions(cache=False)
    parents = ["None"] + list(ranks)
    form = ModalFormData()
    form.title("Create Onistone Rank")
    form.text_field("Internal rank name", "Moderator")
    form.text_field("Displayed title", "Mod")
    form.dropdown("Title color", [name for name, _ in COLOR_OPTIONS], 11)
    form.dropdown("Parent rank", parents)
    form.text_field("Weight", "10", "10")
    form.toggle("Show title in brackets", True)
    form.submit_button("Create rank")

    def submit(admin: Player, response: ModalFormResponse) -> None:
        if response.canceled:
            open_permissions_manager(plugin, admin)
            return
        values = response.formValues
        rank_name = str(values[0]).strip()
        title = str(values[1]).strip() or rank_name
        if not re.fullmatch(r"[A-Za-z0-9 _-]{1,32}", rank_name):
            admin.send_message(
                "§cRank names must be 1-32 letters, numbers, spaces, underscores, or dashes."
            )
            return
        latest = load_permissions(cache=False)
        if _rank_key(latest, rank_name):
            admin.send_message("§cA rank with that name already exists.")
            return
        try:
            color = COLOR_OPTIONS[int(values[2])][1]
            parent = parents[int(values[3])]
            weight = int(str(values[4]).strip())
            brackets = bool(values[5])
            group = apply_rank_appearance(
                {"permissions": {}, "inherits": [], "weight": weight},
                title,
                color,
                True,
                brackets,
                "§r",
            )
            group["inherits"] = [] if parent == "None" else [parent]
            latest[rank_name] = group
            save_permissions(latest, True)
            perms_util.reload_rank_list()
            admin.send_message(f"§aCreated rank §f{rank_name}§a.")
            _show_rank_menu(plugin, admin, rank_name)
        except (ValueError, IndexError) as error:
            admin.send_message(f"§cCould not create rank: {error}")

    _show(form, player, submit)


def _show_rank_assignment(
    plugin: "OnistoneEssentials", player: Player, rank_name: str
) -> None:
    online_players = sorted(plugin.server.online_players, key=lambda item: item.name.lower())
    if not online_players:
        player.send_message("§eThere are no online players to assign.")
        _show_rank_menu(plugin, player, rank_name)
        return
    form = ModalFormData()
    form.title(f"Assign {rank_name}")
    form.dropdown("Online player", [target.name for target in online_players])
    form.submit_button("Assign rank")

    def submit(admin: Player, response: ModalFormResponse) -> None:
        if response.canceled:
            _show_rank_menu(plugin, admin, rank_name)
            return
        index = int(response.formValues[0])
        if index < 0 or index >= len(online_players):
            admin.send_message("§cInvalid player selection.")
            return
        target = online_players[index]
        plugin.db.update_user_data(target.name, "internal_rank", rank_name)
        plugin.reload_custom_perms(target)
        perms_util.invalidate_perm_cache(target.xuid)
        admin.send_message(f"§aAssigned §f{rank_name}§a to §f{target.name}§a.")
        _show_rank_menu(plugin, admin, rank_name)

    _show(form, player, submit)


def open_player_permission_manager(
    plugin: "OnistoneEssentials", player: Player, target_name: str | None = None
) -> None:
    if target_name:
        user = plugin.db.get_offline_user(target_name)
        if not user:
            player.send_message(f"§cPlayer \"{target_name}\" was not found.")
            return
        _show_player_categories(plugin, player, user.name, user.xuid)
        return
    _show_online_player_list(plugin, player)


def _show_online_player_list(plugin: "OnistoneEssentials", player: Player) -> None:
    online_players = sorted(plugin.server.online_players, key=lambda item: item.name.lower())
    form = ActionFormData()
    form.title("Player Permission Overrides")
    form.body("Choose an online player, or use /permissions <player> for an offline player.")
    for target in online_players:
        form.button(target.name)
    form.button("Back")

    def submit(admin: Player, response: ActionFormResponse) -> None:
        if response.canceled:
            return
        selection = int(response.selection)
        if selection == len(online_players):
            open_permissions_manager(plugin, admin)
        elif 0 <= selection < len(online_players):
            target = online_players[selection]
            _show_player_categories(plugin, admin, target.name, target.xuid)

    _show(form, player, submit)


def _show_player_categories(
    plugin: "OnistoneEssentials", player: Player, target_name: str, xuid: str
) -> None:
    explicit = plugin.db.get_permissions(xuid)
    grouped = permission_groups(_all_permissions(explicit))
    categories = list(grouped)
    form = ActionFormData()
    form.title(f"{target_name}: Overrides")
    form.body(
        "Player overrides take priority over their rank. Choose Inherit to remove "
        "an override."
    )
    for category in categories:
        form.button(f"{category}\n§8{len(grouped[category])} permissions")
    form.button("Back")

    def submit(admin: Player, response: ActionFormResponse) -> None:
        if response.canceled:
            return
        selection = int(response.selection)
        if selection < len(categories):
            category = categories[selection]
            _show_player_permission_editor(
                plugin,
                admin,
                target_name,
                xuid,
                category,
                grouped[category],
            )
        else:
            open_permissions_manager(plugin, admin)

    _show(form, player, submit)


def _show_player_permission_editor(
    plugin: "OnistoneEssentials",
    player: Player,
    target_name: str,
    xuid: str,
    category: str,
    permissions: list[str],
) -> None:
    explicit = plugin.db.get_permissions(xuid)
    labels = []
    for permission in permissions:
        state = permission_state_index(explicit, permission)
        marker = ("§7Inherit", "§aAllow", "§cDeny")[state]
        labels.append(f"{permission} — {marker}")
    form = ModalFormData()
    form.title(f"{target_name}: {category}")
    form.dropdown("Permission", labels)
    form.dropdown("Override", list(PERMISSION_STATES))
    form.submit_button("Save override")

    def submit(admin: Player, response: ModalFormResponse) -> None:
        if response.canceled:
            _show_player_categories(plugin, admin, target_name, xuid)
            return
        permission_index = int(response.formValues[0])
        state_index = int(response.formValues[1])
        if permission_index < 0 or permission_index >= len(permissions):
            admin.send_message("§cInvalid permission selection.")
            return
        permission = permissions[permission_index]
        updated = set_permission_state(
            plugin.db.get_permissions(xuid), permission, state_index
        )
        plugin.db.set_permissions(xuid, updated)
        target = plugin.server.get_player(target_name)
        if target:
            plugin.reload_custom_perms(target)
            perms_util.invalidate_perm_cache(target.xuid)
        admin.send_message(
            f"§aSaved §f{permission}§a as §f{PERMISSION_STATES[state_index]}§a "
            f"for §f{target_name}§a."
        )
        _show_player_categories(plugin, admin, target_name, xuid)

    _show(form, player, submit)
