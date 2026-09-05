# Onistone Essentials v3.5.0

This release completes the Onistone rebrand and introduces a guided in-game permissions manager.

## Highlights

- Open `/rank` to manage rank sets from Bedrock forms.
- Select permissions by plugin/category and permission dropdown.
- Set every explicit permission to **Allow**, **Deny**, or **Inherit / neutral**.
- Rename visible rank titles such as `Admin` and select their Minecraft color.
- Configure brackets, suffixes, weights, parent ranks, and online-player rank assignments.
- Open `/permissions` for player-specific overrides.
- Continue using the existing text commands from the server console or command automation.

## Upgrade notes

On first start, existing configuration and databases are copied into `plugins/onistone_essentials/`. Saved rank and player permission nodes are translated to `onistone.*`. Back up the server before upgrading and remove the older wheel from `plugins/` before installing this release.

## Compatibility

- Endstone 0.11.9 / API 0.11
- Bedrock Dedicated Server 1.26.44
- Python 3.10 or newer
