from __future__ import annotations

import sys
import types

from conftest import SRC_PACKAGE, load_source


def load_entityinfo_without_block_sender(monkeypatch):
    class CommandSender:
        pass

    class Mob(CommandSender):
        pass

    class Item(CommandSender):
        pass

    class Player(Mob):
        pass

    class Location:
        def __init__(self, *args):
            self.args = args

    endstone = types.ModuleType("endstone")
    endstone.Player = Player
    actor_module = types.ModuleType("endstone.actor")
    actor_module.Item = Item
    actor_module.Mob = Mob
    command_module = types.ModuleType("endstone.command")
    command_module.CommandSender = CommandSender
    # Deliberately do not expose BlockCommandSender.
    level_module = types.ModuleType("endstone.level")
    level_module.Location = Location

    command_util = types.ModuleType("endstone_primebds.utils.command_util")

    def create_command(name, description, usages, permissions, default="op", aliases=None):
        return (
            {
                name: {
                    "description": description,
                    "usages": usages,
                    "permissions": permissions,
                    "aliases": aliases or [],
                }
            },
            {permissions[0]: {"description": description, "default": default}},
        )

    command_util.create_command = create_command
    target_util = types.ModuleType("endstone_primebds.utils.target_selector_util")
    target_util.get_target_entity = lambda _sender: None

    for name, module in {
        "endstone": endstone,
        "endstone.actor": actor_module,
        "endstone.command": command_module,
        "endstone.level": level_module,
        "endstone_primebds.utils.command_util": command_util,
        "endstone_primebds.utils.target_selector_util": target_util,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    if "endstone_primebds.utils.entity_hotspot_teleport" not in sys.modules:
        load_source(
            "endstone_primebds.utils.entity_hotspot_teleport",
            SRC_PACKAGE / "utils" / "entity_hotspot_teleport.py",
        )
    module = load_source(
        "entityinfo_without_block_sender",
        SRC_PACKAGE / "commands" / "Misc" / "entityinfo.py",
    )
    return module, Player


class ExplodingLevel:
    @property
    def actors(self):
        raise AssertionError("help/cached operations must not enumerate actors")


class Service:
    def __init__(self):
        self.started = 0

    def sender_key(self, sender):
        return f"console:{sender.name}"

    def get_selected(self, owner):
        raise LookupError("no saved scan")

    def start_scan(self, owner, mode, filters, reader, callback):
        self.started += 1
        return True, "Started loaded-entity scan EH-0001."


class Console:
    name = "Server"

    def __init__(self, permissions):
        self.permissions = permissions
        self.messages = []

    def has_permission(self, permission):
        return permission in self.permissions

    def send_message(self, message):
        self.messages.append(message)


def plugin():
    instance = types.SimpleNamespace()
    instance.entity_hotspot_service = Service()
    instance.server = types.SimpleNamespace(level=ExplodingLevel())
    return instance


def test_permissions_are_explicitly_registered_but_not_all_command_level(monkeypatch):
    module, _player = load_entityinfo_without_block_sender(monkeypatch)

    assert module.BlockCommandSender is None
    assert module.command["entityinfo"]["permissions"] == [
        "onistone.command.entityinfo"
    ]
    assert set(module.permission) == {
        "onistone.command.entityinfo",
        "onistone.command.entityinfo.hotspots",
        "onistone.command.entityinfo.hotspots.teleport",
    }


def test_command_registration_accepts_case_insensitive_subcommands(monkeypatch):
    module, _player = load_entityinfo_without_block_sender(monkeypatch)
    usages = module.command["entityinfo"]["usages"]

    assert usages[0] == "/entityinfo"
    assert usages[1] == "/entityinfo <action: str>"
    assert usages[-1].endswith("<arg5: str>")
    assert all(": string>" not in usage for usage in usages)


def test_console_can_start_scan_and_help_does_not_enumerate_actors(monkeypatch):
    module, _player = load_entityinfo_without_block_sender(monkeypatch)
    sender = Console({module.HOTSPOT_PERMISSION})
    instance = plugin()

    assert module.handler(instance, sender, ["hotspots", "help"]) is True
    assert module.handler(instance, sender, ["Hotspots"]) is True
    assert instance.entity_hotspot_service.started == 1


def test_page_request_without_snapshot_never_silently_starts_scan(monkeypatch):
    module, _player = load_entityinfo_without_block_sender(monkeypatch)
    sender = Console({module.HOTSPOT_PERMISSION})
    instance = plugin()

    assert module.handler(instance, sender, ["hotspots", "2"]) is False
    assert instance.entity_hotspot_service.started == 0
    assert "no saved scan" in sender.messages[-1]


def test_hotspot_permission_is_checked_and_console_teleport_is_player_only(monkeypatch):
    module, _player = load_entityinfo_without_block_sender(monkeypatch)
    sender = Console(set())
    instance = plugin()

    assert module.handler(instance, sender, ["hotspots"]) is False
    assert module.HOTSPOT_PERMISSION in sender.messages[-1]
    assert module.handler(instance, sender, ["tp", "1"]) is False
    assert "Only a player" in sender.messages[-1]
