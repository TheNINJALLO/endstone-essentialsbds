<!-- endstone-professional-header:start -->
<p align="center">
  <img src="docs/assets/banner.svg" width="100%" alt="Onistone Essentials &mdash; server administration and quality-of-life tools for Endstone">
</p>

<p align="center">
  <a href="https://github.com/TheNINJALLO/endstone-essentialsbds/actions/workflows/wheel-release.yml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/TheNINJALLO/endstone-essentialsbds/wheel-release.yml?branch=main&amp;style=for-the-badge&amp;logo=githubactions&amp;logoColor=white&amp;label=Build"></a>
  <a href="https://github.com/TheNINJALLO/endstone-essentialsbds/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/TheNINJALLO/endstone-essentialsbds?display_name=tag&amp;style=for-the-badge&amp;label=Release"></a>
</p>

<p align="center">
  <img alt="Endstone 0.11.9" src="https://img.shields.io/badge/Endstone-0.11.9-52b7a8?style=flat-square">
  <img alt="API 0.11" src="https://img.shields.io/badge/API-0.11-63b8ff?style=flat-square">
  <img alt="BDS 1.26.44" src="https://img.shields.io/badge/BDS-1.26.44-8b7dff?style=flat-square">
  <img alt="Python >=3.10" src="https://img.shields.io/badge/Python-%3E=3.10-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white">
</p>

<p align="center">
  <strong>An essentials plugin for diagnostics, stability, and quality of life on Minecraft Bedrock Edition.</strong>
</p>

<p align="center">
  <a href="#what-it-does">What it does</a> &bull;
  <a href="#how-to-use">How to use</a> &bull;
  <a href="#commands-and-permissions">Commands</a> &bull;
  <a href="commands.md">Command guide</a> &bull;
  <a href="#install">Install</a> &bull;
  <a href="https://github.com/TheNINJALLO/endstone-essentialsbds/releases">Releases</a>
</p>

## Overview

An essentials plugin for diagnostics, stability, and quality of life on Minecraft Bedrock Edition. This release is aligned with Endstone 0.11.9 and Minecraft Bedrock Dedicated Server 1.26.44, and is distributed as a Python wheel for direct installation in an Endstone server.

## What it does

- Provides a broad essentials suite covering gamemodes, item tools, messaging, moderation, teleport utilities, diagnostics, permissions, and ranks.
- Loads each command as a separate configurable module so unwanted commands can be disabled.
- Adds configurable chat, join/leave, combat, monitoring, multiworld, and server-stability behavior.
- Includes an in-game permissions manager for rank sets, per-player overrides, inheritance, and rank appearance.
- Finds the busiest loaded entity chunks and connected dense-chunk groups with stable, per-administrator scan results and guarded inspection teleports.

## How to use

1. Start once to generate `plugins/onistone_essentials/` with the main settings, command-module configuration, permissions, databases, and rules files.
2. Run `/rank` as an operator to open the **Onistone Permissions** manager.
3. Select a rank set, select a permission category, choose a permission from the dropdown, and set it to **Allow**, **Deny**, or **Inherit / neutral**.
4. Open **Edit title, color & settings** to rename a visible title such as `Admin`, choose its Minecraft color, toggle brackets, set inheritance, and adjust weight or suffix.
5. Use **Manage player overrides** or `/permissions <player>` when one player needs an exception to their rank.

Existing installations are migrated automatically on first start. Configuration, databases, ranks, and player permission overrides are retained, and old permission entries are translated to the `onistone.*` namespace.

### Find an entity hotspot

Operators can run the following inspection workflow:

```text
/entityinfo hotspots
/entityinfo hotspots groups
/entityinfo hotspots detail 1
/entityinfo tp 1
```

The first command performs an on-demand scan of actors currently exposed by Endstone's loaded-actor API. The next commands reuse that administrator's immutable saved scan; viewing another page, switching ranking mode, opening a detail, or teleporting does not silently enumerate actors again. Use `/entityinfo hotspots refresh` when a new sample is needed.

Chunk mode ranks vertical chunk columns. Group mode joins qualifying chunks in the same dimension through eight-neighbor X/Z adjacency, including diagonals. Groups are connected dense-chunk regions, not radius-based or three-dimensional clusters, and a chain of chunks may create a sprawling group. The detail output shows its extent and peak chunk.

Players are excluded by default. Named, tamed, and custom actors remain eligible, and custom actors are classified through Endstone's `Mob`, `Item`, and `Player` types rather than a vanilla entity list. Each dropped item actor counts as one entity; exposed stack quantities are reported separately and never increase the entity count.

> [!NOTE]
> Results cover loaded actors only. Unloaded/saved entities and offline world files are not searched, no chunks are force-loaded, and multi-tick collection is a sampling window rather than an atomic world snapshot. A high entity count is a diagnostic lead, not proof of server lag.

See [commands.md](commands.md) for every hotspot syntax, filters, permissions, output semantics, and configuration option.

### Permissions GUI

- `/rank` or `/rank gui` opens the complete rank-set manager.
- `/permissions` opens the online-player override picker.
- `/permissions <player>` edits an online or known offline player's overrides.
- `/permissionslist [player]` remains available for a read-only permission audit.
- Existing `/rank set`, `/rank perm`, `/rank prefix`, `/rank suffix`, `/rank inherit`, and direct `/permissions ... settrue|setfalse|setneutral` commands remain available for console use and automation.

## Commands and permissions

| Command / usage | What it does | Access |
|---|---|---|
| `/gma [player: player]` | Sets your game mode to adventure! | `onistone.command.gma` |
| `/gmc [player: player]` | Set your own or another player's game mode to Creative | `onistone.command.gmc` |
| `/gms [player: player]` | Set your own or another player's game mode to Survival | `onistone.command.gms` |
| `/gmsp [player: player]` | Sets your game mode to spectator! | `onistone.command.gmsp` |
| `/gmt [player: player]` | Toggles you between survival and creative mode! | `onistone.command.gmt` |
| `/iteminfo [player: player] (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotTypeInfo: slotTypeInfo] [slot: int]` | Check item data! | `onistone.command.iteminfo` |
| `/itemlore <player: player> (add)<add_lore: add_lore> <item_lore: string> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeAddLore] [slot: int]`<br>`/itemlore <player: player> (set)<set_lore: set_lore> <replaced_lore: string> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeSetLore] [slot: int]`<br>`/itemlore <player: player> (delete)<delete_lore: delete_lore> [item_lore_line: int] (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeDeleteLore] [slot: int]`<br>`/itemlore <player: player> (clear)<clear_lore: clear_lore> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeSlotClearLore] [slot: int]`<br><sub>Aliases: `/lore`</sub> | Modify item lore data! | `onistone.command.itemlore` |
| `/itemname <player: player> (set)<set_name: set_name> <item_name: string> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeSetName] [slot: int]`<br>`/itemname <player: player> (clear)<clear_name: clear_name> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeClearName] [slot: int]` | Modify item name data! | `onistone.command.itemname` |
| `/itemtag <player: player> (unbreakable)<itemTag: itemTag> <is: bool> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotTypeTag: slotTypeTag] [slot: int]` | Modify item tags! | `onistone.command.itemtag` |
| `/more` | Sets a full stack to the held item! | `onistone.command.more` |
| `/repair [player: player]` | Repairs the item in hand! | `onistone.command.repair`, `onistone.command.repair.other` |
| `/spectate [player: player]` | Warps you to a non-spectating player! | `onistone.command.spectate` |
| `/broadcast <message: message>` | Send a server-wide notification! | `onistone.command.broadcast` |
| `/clearchat` | Adds 100 empty lines to chat! | `onistone.command.clearchat` |
| `/note <player: player> (clear)<note_clear: note_clear>`<br>`/note <player: player> [page: int]`<br>`/note <player: player> (remove)<note_remove: note_remove> <id: int>`<br>`/note <player: player> (add)<note_add: note_add> <message: message>` | Manage mod notes on players! | `onistone.command.note` |
| `/popup <player: player> <text: message>` | Sends a custom popup message! | `onistone.command.popup` |
| `/tip <player: player> <text: message>` | Sends a custom tip message! | `onistone.command.tip` |
| `/toast <player: player> <title: string> <text: message>` | Sends a custom toast message! | `onistone.command.toast` |
| `/blockinfo [location: pos]` | Prints info of the facing block! | `onistone.command.blockinfo` |
| `/blockscan (disable)[blockscan: blockscan]` | Continuously show information about the block you're looking at. | `onistone.command.blockscan` |
| `/check <player: player> (info\|mod\|jail\|network\|world)[info: info]`<br><sub>Aliases: `/seen`</sub> | Checks a player's client info! | `onistone.command.check` |
| `/entityinfo`<br>`/entityinfo list [page]`<br>`/entityinfo hotspots [page]`<br>`/entityinfo hotspots chunks [page]`<br>`/entityinfo hotspots groups [page]`<br>`/entityinfo hotspots detail <rank>`<br>`/entityinfo hotspots refresh`<br>`/entityinfo hotspots help`<br>`/entityinfo hotspots filter <chunks\|groups> <dimension> <type-or-category> [page]`<br>`/entityinfo tp <rank>` | Inspect a targeted entity, list loaded entity types, or find and safely inspect loaded-entity hotspots. | Base: `onistone.command.entityinfo`<br>Scan/view: `onistone.command.entityinfo.hotspots`<br>Teleport: `onistone.command.entityinfo.hotspots.teleport` |
| `/heal [player: player]` | Sets player health to full! | `onistone.command.heal`, `onistone.command.heal.other` |
| `/ping [player: player]` | Checks the server ping! | `onistone.command.ping` |
| `/jail <player: player> <jail: string> <duration_number: int> (second\|minute\|hour\|day\|week\|month\|year)<duration_length: jail_length> [reason: message]`<br>`/jail <player: player> <jail: string> (forever)<perm_jail: perm_jail> [reason: message]` | Jails a player to a specified area! | `onistone.command.jail` |
| `/jails (list)[list_jails: list_jails]`<br>`/jails (create\|delete\|tp)<jail_action: jail_action> <jail: string> [location: pos]` | Manages server jails! | `onistone.command.jails` |
| `/nameban <player: player> <duration_number: int> (second\|minute\|hour\|day\|week\|month\|year)<duration_length: name_ban_length> [reason: message]`<br>`/nameban <player: player> (forever)<name_ban: name_ban> [reason: message]` | Bans a player's name from the server, either temporarily or permanently! | `onistone.command.nameban` |
| `/unnameban <player: player>` | Removes an active name ban from a player! | `onistone.command.unnameban` |
| `/permban <player: player> [reason: message]` | Permanently bans a player from the server! | `onistone.command.permban` |
| `/punishments <player: player> [page: int]`<br>`/punishments <player: player> (remove\|clear) <punishment_removal: remove_punishment_log>` | Manage punishment history of a specified player! | `onistone.command.punishments` |
| `/removeban <player: player>`<br>`/removeban <player: player> (ip)<perm_removeban: perm_removeban>` | Removes an active ban from a player! | `onistone.command.removeban`, `onistone.command.pardon` |
| `/tempban <player: player> <duration_number: int> (second\|minute\|hour\|day\|week\|month\|year)<duration_length: ban_length> [reason: message]` | Temporarily bans a player from the server! | `onistone.command.tempban` |
| `/unjail <player: player>` | Free a jailed player! | `onistone.command.unjail` |
| `/unwarn <player: player> (clear)<warn_action: warn_action>`<br>`/unwarn <player: player> [id: int]` | Remove a warning or clear all warnings from a player! | `onistone.command.unwarn` |
| `/vanish` | Completely hide your server visibility! | `onistone.command.vanish` |
| `/warn <player: player> <reason: string> [duration_number: int] (second\|minute\|hour\|day\|week\|month\|year)[duration_length: warn_length]` | Warn a player that they are breaking a rule! | `onistone.command.warn` |
| `/warnings <player: player> [page: int]`<br>`/warnings <player: player> (delete\|clear)<del_warn: del_warn> [id: int]` | List warnings or permanently delete warnings from a player! | `onistone.command.warnings` |
| `/bottom` | Warps you to the nearest air pocket below you! | `onistone.command.bottom` |
| `/offlinetp [player: player]`<br><sub>Aliases: `/otp`</sub> | Teleport to where a player last logged out. | `onistone.command.offlinetp` |
| `/spawn` | Warps you to the spawn! | `onistone.command.spawn` |
| `/top` | Warps you to the topmost block with air! | `onistone.command.top` |
| `/monitor (server\|packets\|disable)[debug: debug]` | Monitor server performance in real time! | `onistone.command.monitor` |
| `/permissions`<br>`/permissions <player: player>`<br>`/permissions <player: player> (settrue\|setfalse\|setneutral)<set_perm: set_perm> <perm: string>`<br><sub>Aliases: `/perms`</sub> | Opens the player-override GUI or directly updates a player permission. | `onistone.command.permissions` |
| `/permissionslist`<br><sub>Aliases: `/permslist`</sub> | View the global or player-specific permissions list! | `onistone.command.permissionslist` |
| `/rank`<br>`/rank gui`<br>`/rank (set)<rank_set: rank_set> <player: player> <rank: string>`<br>`/rank (prefix\|suffix)<rank_meta: rank_meta> <rank: string> <meta: message>`<br>`/rank (perm)<rank_perm: rank_perm> (add\|remove)<perm_action: perm_action> <rank: string> <perm: string> [state: bool]`<br>`/rank (weight)<rank_weight: rank_weight> <rank: string> <weight: int>`<br>`/rank (inherit)<rank_inherit: rank_inherit> <rank_child: string> <rank_parent: string>`<br>`/rank (create\|delete\|list\|info)<rank_action: rank_action> [rank: message]` | Opens the rank GUI or directly manages ranks. | `onistone.command.rank` |
| `/reloadscripts`<br><sub>Aliases: `/rscripts`, `/rs`</sub> | Reloads the server scripts! | `onistone.command.reloadscripts` |

## Compatibility

| Component | Supported version |
|---|---|
| Endstone | `0.11.9` |
| Endstone API | `0.11` |
| Bedrock Dedicated Server | `1.26.44` |
| Python | `>=3.10` |
| Plugin release | `v3.5.3` |

## Install

Download the wheel from the matching GitHub release:

```bash
gh release download v3.5.3 --repo TheNINJALLO/endstone-essentialsbds --pattern "*.whl"
```

Copy the downloaded wheel into the server's `plugins/` directory, remove any older wheel for the same plugin, and restart Endstone.

> [!NOTE]
> Starting with v3.5.1, the wheel is named `endstone_onistone_essentials-<version>-py3-none-any.whl`. Remove older `endstone_essentialsbds-*.whl` files before restarting so Endstone does not discover both distributions.

> [!IMPORTANT]
> Use Endstone `0.11.9` with BDS `1.26.44`. Back up worlds and plugin data before upgrading a production server.

## Configuration and secrets

Runtime databases, logs, local `.env` files, server directories, and root `config.toml` files are excluded from source releases. When an example configuration is provided, copy it locally and keep live tokens, passwords, webhook URLs, and server identifiers out of Git.

Entity hotspot defaults are added under `modules.entity_hotspots` in `plugins/onistone_essentials/config.json`. Missing keys are merged on startup without replacing existing values:

```json
{
  "modules": {
    "entity_hotspots": {
      "enabled": true,
      "write_report_file": true,
      "results_per_page": 5,
      "include_players": false,
      "scan_cooldown_seconds": 15,
      "snapshot_lifetime_seconds": 300,
      "max_retained_snapshots": 16,
      "max_concurrent_scans": 1,
      "max_actors": 20000,
      "max_scan_seconds": 8.0,
      "actors_per_tick": 750,
      "dense_chunk_threshold": 10,
      "teleport_enabled": true,
      "teleport_horizontal_radius": 4,
      "teleport_vertical_radius": 32,
      "teleport_max_candidates": 512
    }
  }
}
```

Every completed scan also atomically replaces the easy-to-read Markdown report at `plugins/onistone_essentials/entity_hotspot_report.md`. It contains the full summary plus every ranked chunk and dense group. Report formatting and disk I/O run on one background worker so large reports do not block the server tick; set `write_report_file` to `false` to disable the file.

Endstone 0.11.9 exposes the loaded actor collection as one indivisible operation, so `actors_per_tick` bounds actor validation and primitive-data capture after that measured acquisition; it cannot bound the initial collection call. Hitting the actor, duration, or access limits marks the result `INCOMPLETE`.

## Release automation

Every `v*` tag runs [the wheel release workflow](.github/workflows/wheel-release.yml), builds the package in a clean GitHub runner, stores the wheel as a workflow artifact, and attaches it to the matching GitHub release.
<!-- endstone-professional-header:end -->
