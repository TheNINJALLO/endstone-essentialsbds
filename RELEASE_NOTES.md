# Onistone Essentials v3.5.1

This release fixes Endstone plugin discovery and adds bounded entity-hotspot diagnostics.

## Highlights

- Corrects the distribution name to `endstone-onistone-essentials`, matching the `onistone_essentials` entry point required by Endstone.
- Adds bounded, paginated entity-hotspot scans to `/entityinfo` for finding dense chunks and entity clusters.
- Adds guarded hotspot teleportation with safe-location selection and configurable scan limits.
- Adds automatic snapshot expiry, concurrency limits, and incomplete-result reporting for busy servers.
- Adds regression coverage for entry-point metadata, hotspot aggregation, scan budgeting, teleport safety, and command behavior.

## Upgrade notes

The wheel filename changes from `endstone_essentialsbds-*.whl` to `endstone_onistone_essentials-*.whl`. Remove the old wheel before installing v3.5.1 or Endstone may discover both distributions. The Python package and `plugins/onistone_essentials/` data folder are unchanged, so existing configuration and databases remain compatible.

## Compatibility

- Endstone 0.11.9 / API 0.11
- Bedrock Dedicated Server 1.26.44
- Python 3.10 or newer
