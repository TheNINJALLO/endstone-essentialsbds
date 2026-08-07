<!-- endstone-professional-header:start -->
<p align="center">
  <img src="docs/assets/banner.svg" width="100%" alt="Endstone EssentialsBDS &mdash; An essentials plugin for diagnostics, stability, and quality of life on Minecraft Bedrock Edition">
</p>

<p align="center">
  <a href="https://github.com/TheNINJALLO/endstone-essentialsbds/actions/workflows/wheel-release.yml"><img alt="Build" src="https://img.shields.io/github/actions/workflow/status/TheNINJALLO/endstone-essentialsbds/wheel-release.yml?branch=main&amp;style=for-the-badge&amp;logo=githubactions&amp;logoColor=white&amp;label=Build"></a>
  <a href="https://github.com/TheNINJALLO/endstone-essentialsbds/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/TheNINJALLO/endstone-essentialsbds?display_name=tag&amp;style=for-the-badge&amp;label=Release"></a>
</p>

<p align="center">
  <img alt="Endstone 0.11.8" src="https://img.shields.io/badge/Endstone-0.11.8-52b7a8?style=flat-square">
  <img alt="API 0.11" src="https://img.shields.io/badge/API-0.11-63b8ff?style=flat-square">
  <img alt="BDS 1.26.40" src="https://img.shields.io/badge/BDS-1.26.40-8b7dff?style=flat-square">
  <img alt="Python >=3.10" src="https://img.shields.io/badge/Python-%3E=3.10-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white">
</p>

<p align="center">
  <strong>An essentials plugin for diagnostics, stability, and quality of life on Minecraft Bedrock Edition.</strong>
</p>

<p align="center">
  <a href="#what-it-does">What it does</a> &bull;
  <a href="#how-to-use">How to use</a> &bull;
  <a href="#commands-and-permissions">Commands</a> &bull;
  <a href="#install">Install</a> &bull;
  <a href="https://github.com/TheNINJALLO/endstone-essentialsbds/releases">Releases</a>
</p>

## Overview

An essentials plugin for diagnostics, stability, and quality of life on Minecraft Bedrock Edition. This release is aligned with Endstone 0.11.8 and Minecraft Bedrock Dedicated Server 1.26.40, and is distributed as a Python wheel for direct installation in an Endstone server.

## What it does

- Provides a broad essentials suite covering gamemodes, item tools, messaging, moderation, teleport utilities, diagnostics, permissions, and ranks.
- Loads each command as a separate configurable module so unwanted commands can be disabled.
- Adds configurable chat, join/leave, combat, monitoring, multiworld, and server-stability behavior.

## How to use

1. Start once to generate the main settings, command-module configuration, permissions, and rules files.
2. Disable command modules you do not want and review Discord/webhook fields before placing the server in production.
3. Grant the `primebds.command.*` permissions through your permission manager; most administrative commands default to operators.
4. Use `/permissionslist` to inspect permission data and `/reloadscripts` after supported configuration or script changes.

## Commands and permissions

| Command / usage | What it does | Access |
|---|---|---|
| `/gma [player: player]` | Sets your game mode to adventure! | `primebds.command.gma` |
| `/gmc [player: player]` | Set your own or another player's game mode to Creative | `primebds.command.gmc` |
| `/gms [player: player]` | Set your own or another player's game mode to Survival | `primebds.command.gms` |
| `/gmsp [player: player]` | Sets your game mode to spectator! | `primebds.command.gmsp` |
| `/gmt [player: player]` | Toggles you between survival and creative mode! | `primebds.command.gmt` |
| `/iteminfo [player: player] (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotTypeInfo: slotTypeInfo] [slot: int]` | Check item data! | `primebds.command.iteminfo` |
| `/itemlore <player: player> (add)<add_lore: add_lore> <item_lore: string> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeAddLore] [slot: int]`<br>`/itemlore <player: player> (set)<set_lore: set_lore> <replaced_lore: string> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeSetLore] [slot: int]`<br>`/itemlore <player: player> (delete)<delete_lore: delete_lore> [item_lore_line: int] (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeDeleteLore] [slot: int]`<br>`/itemlore <player: player> (clear)<clear_lore: clear_lore> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeSlotClearLore] [slot: int]`<br><sub>Aliases: `/lore`</sub> | Modify item lore data! | `primebds.command.itemlore` |
| `/itemname <player: player> (set)<set_name: set_name> <item_name: string> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeSetName] [slot: int]`<br>`/itemname <player: player> (clear)<clear_name: clear_name> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotType: slotTypeClearName] [slot: int]` | Modify item name data! | `primebds.command.itemname` |
| `/itemtag <player: player> (unbreakable)<itemTag: itemTag> <is: bool> (slot\|helmet\|chestplate\|leggings\|boots\|mainhand\|offhand)[slotTypeTag: slotTypeTag] [slot: int]` | Modify item tags! | `primebds.command.itemtag` |
| `/more` | Sets a full stack to the held item! | `primebds.command.more` |
| `/repair [player: player]` | Repairs the item in hand! | `primebds.command.repair`, `primebds.command.repair.other` |
| `/spectate [player: player]` | Warps you to a non-spectating player! | `primebds.command.spectate` |
| `/broadcast <message: message>` | Send a server-wide notification! | `primebds.command.broadcast` |
| `/clearchat` | Adds 100 empty lines to chat! | `primebds.command.clearchat` |
| `/note <player: player> (clear)<note_clear: note_clear>`<br>`/note <player: player> [page: int]`<br>`/note <player: player> (remove)<note_remove: note_remove> <id: int>`<br>`/note <player: player> (add)<note_add: note_add> <message: message>` | Manage mod notes on players! | `primebds.command.note` |
| `/popup <player: player> <text: message>` | Sends a custom popup message! | `primebds.command.popup` |
| `/tip <player: player> <text: message>` | Sends a custom tip message! | `primebds.command.tip` |
| `/toast <player: player> <title: string> <text: message>` | Sends a custom toast message! | `primebds.command.toast` |
| `/blockinfo [location: pos]` | Prints info of the facing block! | `primebds.command.blockinfo` |
| `/blockscan (disable)[blockscan: blockscan]` | Continuously show information about the block you're looking at. | `primebds.command.blockscan` |
| `/check <player: player> (info\|mod\|jail\|network\|world)[info: info]`<br><sub>Aliases: `/seen`</sub> | Checks a player's client info! | `primebds.command.check` |
| `/entityinfo (list)[entity_action: entity_action] [page: int]` | Check entity information! | `primebds.command.entityinfo` |
| `/heal [player: player]` | Sets player health to full! | `primebds.command.heal`, `primebds.command.heal.other` |
| `/ping [player: player]` | Checks the server ping! | `primebds.command.ping` |
| `/jail <player: player> <jail: string> <duration_number: int> (second\|minute\|hour\|day\|week\|month\|year)<duration_length: jail_length> [reason: message]`<br>`/jail <player: player> <jail: string> (forever)<perm_jail: perm_jail> [reason: message]` | Jails a player to a specified area! | `primebds.command.jail` |
| `/jails (list)[list_jails: list_jails]`<br>`/jails (create\|delete\|tp)<jail_action: jail_action> <jail: string> [location: pos]` | Manages server jails! | `primebds.command.jails` |
| `/nameban <player: player> <duration_number: int> (second\|minute\|hour\|day\|week\|month\|year)<duration_length: name_ban_length> [reason: message]`<br>`/nameban <player: player> (forever)<name_ban: name_ban> [reason: message]` | Bans a player's name from the server, either temporarily or permanently! | `primebds.command.nameban` |
| `/unnameban <player: player>` | Removes an active name ban from a player! | `primebds.command.unnameban` |
| `/permban <player: player> [reason: message]` | Permanently bans a player from the server! | `primebds.command.permban` |
| `/punishments <player: player> [page: int]`<br>`/punishments <player: player> (remove\|clear) <punishment_removal: remove_punishment_log>` | Manage punishment history of a specified player! | `primebds.command.punishments` |
| `/removeban <player: player>`<br>`/removeban <player: player> (ip)<perm_removeban: perm_removeban>` | Removes an active ban from a player! | `primebds.command.removeban`, `primebds.command.pardon` |
| `/tempban <player: player> <duration_number: int> (second\|minute\|hour\|day\|week\|month\|year)<duration_length: ban_length> [reason: message]` | Temporarily bans a player from the server! | `primebds.command.tempban` |
| `/unjail <player: player>` | Free a jailed player! | `primebds.command.unjail` |
| `/unwarn <player: player> (clear)<warn_action: warn_action>`<br>`/unwarn <player: player> [id: int]` | Remove a warning or clear all warnings from a player! | `primebds.command.unwarn` |
| `/vanish` | Completely hide your server visibility! | `primebds.command.vanish` |
| `/warn <player: player> <reason: string> [duration_number: int] (second\|minute\|hour\|day\|week\|month\|year)[duration_length: warn_length]` | Warn a player that they are breaking a rule! | `primebds.command.warn` |
| `/warnings <player: player> [page: int]`<br>`/warnings <player: player> (delete\|clear)<del_warn: del_warn> [id: int]` | List warnings or permanently delete warnings from a player! | `primebds.command.warnings` |
| `/bottom` | Warps you to the nearest air pocket below you! | `primebds.command.bottom` |
| `/offlinetp [player: player]`<br><sub>Aliases: `/otp`</sub> | Teleport to where a player last logged out. | `primebds.command.offlinetp` |
| `/spawn` | Warps you to the spawn! | `primebds.command.spawn` |
| `/top` | Warps you to the topmost block with air! | `primebds.command.top` |
| `/monitor (server\|packets\|disable)[debug: debug]` | Monitor server performance in real time! | `primebds.command.monitor` |
| `/permissions <player: player> (settrue\|setfalse\|setneutral)<set_perm: set_perm> <perm: string>`<br><sub>Aliases: `/perms`</sub> | Sets the internal permissions for a player! | `primebds.command.permissions` |
| `/permissionslist`<br><sub>Aliases: `/permslist`</sub> | View the global or player-specific permissions list! | `primebds.command.permissionslist` |
| `/rank (set)<rank_set: rank_set> <player: player> <rank: string>`<br>`/rank (prefix\|suffix)<rank_meta: rank_meta> <rank: string> <meta: message>`<br>`/rank (perm)<rank_perm: rank_perm> (add\|remove)<perm_action: perm_action> <rank: string> <perm: string> [state: bool]`<br>`/rank (weight)<rank_weight: rank_weight> <rank: string> <weight: int>`<br>`/rank (inherit)<rank_inherit: rank_inherit> <rank_child: string> <rank_parent: string>`<br>`/rank (create\|delete\|list\|info)<rank_action: rank_action> [rank: message]` | Sets the internal rank for a player! | `primebds.command.rank` |
| `/reloadscripts`<br><sub>Aliases: `/rscripts`, `/rs`</sub> | Reloads the server scripts! | `primebds.command.reloadscripts` |

## Compatibility

| Component | Supported version |
|---|---|
| Endstone | `0.11.8` |
| Endstone API | `0.11` |
| Bedrock Dedicated Server | `1.26.40` |
| Python | `>=3.10` |
| Plugin release | `v3.4.4` |

## Install

Download the wheel from the matching GitHub release:

```bash
gh release download v3.4.4 --repo TheNINJALLO/endstone-essentialsbds --pattern "*.whl"
```

Copy the downloaded wheel into the server's `plugins/` directory, remove any older wheel for the same plugin, and restart Endstone.

> [!IMPORTANT]
> Use Endstone `0.11.8` with BDS `1.26.40`. Back up worlds and plugin data before upgrading a production server.

## Configuration and secrets

Runtime databases, logs, local `.env` files, server directories, and root `config.toml` files are excluded from source releases. When an example configuration is provided, copy it locally and keep live tokens, passwords, webhook URLs, and server identifiers out of Git.

## Release automation

Every `v*` tag runs [the wheel release workflow](.github/workflows/wheel-release.yml), builds the package in a clean GitHub runner, stores the wheel as a workflow artifact, and attaches it to the matching GitHub release.
<!-- endstone-professional-header:end -->

---

## Project guide

This is PrimeBDS, an essentials plugin for diagnostics, stability, and quality of life on Minecraft Bedrock Edition.
This plugin runs on the Endstone plugin loader: https://endstone.readthedocs.io/en/latest/

# Features
The full documentation can be found on the [wiki](https://github.com/PrimeStrat/primebds/wiki)

# How do I install?
1. Create an [endstone](https://endstone.readthedocs.io/en/latest/) server
   - [Bisect Hosting](https://www.bisecthosting.com/) is partnered with Endstone and supports all of the setup for an Endstone server!
   - Endstone servers allow you to install plugins without losing any vanilla features, find out more [here](https://endstone.readthedocs.io/en/latest/)
3. Download the .whl file from the latest [release](https://github.com/PrimeStrat/primebds/releases)
4. Drag and drop it into your plugins folder
