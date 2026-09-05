from typing import TYPE_CHECKING

from endstone.event import PlayerGameModeChangeEvent, PlayerInteractActorEvent, PlayerTeleportEvent, PlayerDeathEvent
from endstone_primebds.utils.config_util import load_config

if TYPE_CHECKING:
    from endstone_primebds.primebds import OnistoneEssentials

def handle_gamemode_event(self: "OnistoneEssentials", ev: PlayerGameModeChangeEvent):
    self.db.update_user_data(ev.player.name, "gamemode", ev.new_game_mode.value)

def handle_teleport_event(self: "OnistoneEssentials", ev: PlayerTeleportEvent):
    config = load_config()
    teleports = config["modules"]["back"]["save_unnatural_teleports"]
    if teleports:
        self.serverdb.set_last_warp(ev.from_location, ev.player.xuid, ev.player.name)
    return

def handle_death_event(self: "OnistoneEssentials", ev: PlayerDeathEvent):
    config = load_config()
    deaths = config["modules"]["back"]["save_death_locations"]
    if deaths:
        self.serverdb.set_last_warp(ev.player.location, ev.player.xuid, ev.player.name)
    return

def handle_interact_event(self: "OnistoneEssentials", ev: PlayerInteractActorEvent):
    if self.db.get_mod_log(ev.player.xuid).is_jailed:
        ev.is_cancelled = True
    elif not self.gamerules.get("can_interact", 1):
        ev.is_cancelled = True
