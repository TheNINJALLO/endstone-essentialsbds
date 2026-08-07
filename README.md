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
  <a href="#overview">Overview</a> &bull;
  <a href="#compatibility">Compatibility</a> &bull;
  <a href="#install">Install</a> &bull;
  <a href="https://github.com/TheNINJALLO/endstone-essentialsbds/releases">Releases</a>
</p>

## Overview

An essentials plugin for diagnostics, stability, and quality of life on Minecraft Bedrock Edition. This release is aligned with Endstone 0.11.8 and Minecraft Bedrock Dedicated Server 1.26.40, and is distributed as a Python wheel for direct installation in an Endstone server.

## Capabilities

-

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
