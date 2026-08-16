# Changelog

All notable changes to Nostalgia Launcher, newest first.

## 0.2.7
- **Instances are real now.** Each instance is its own modpack with a separate
  mods / saves / config / resourcepacks folder, so mods in one instance never
  clash with another. The heavy version, library, asset and Java store stays
  shared, so instances are cheap.
- **New Instance** asks for a name and a version (Fabric versions included).
- The **Mods** and **Resource Packs** tabs got an instance picker — choose which
  instance a download installs into.
- Your old shared mods are migrated into your first instance automatically.

## 0.2.6
- **Fixed: old Minecraft versions wouldn't launch on Apple Silicon Macs.**
  Mojang ships no Java 8/16/17-legacy runtime for arm64, so anything up to 1.17
  now runs the x86_64 runtime under Rosetta (with matching natives).
- Fixed pre-1.13 versions crashing on macOS by adding the required
  `-XstartOnFirstThread` flag.

## 0.2.5
- **Updates now install themselves.** Click *Install update* and the launcher
  downloads and installs the new version in place — Linux via a single password
  prompt, Windows via a silent per-user installer — then restarts.

## 0.2.4
- **Discover** in Browse Modrinth: opens straight into popular picks, with sort
  (Relevance / Popular / Newest) and loader filters (Fabric / Forge / NeoForge /
  Quilt), plus a preview image for every mod.

## 0.2.3
- **Linux `.deb` installer** for Mint / Ubuntu / Debian, built by CI.
- **Change Client ID** added to the account menu.
- Groundwork for Windows code-signing (activates when a certificate is set).

## 0.2.2
- **Fixed: Minecraft wouldn't launch on Windows** (the bundled Java install
  crashed on a path-separator bug).
- **Update checker**: the launcher tells you when a newer release is out.

## 0.2.1
- New default background, and a friendlier Microsoft sign-in that asks for your
  Azure client ID the first time.
- Fixed the memory slider capping at 8 GB on Windows and macOS.

## 0.2.0
- First packaged builds: Windows `.exe` and macOS `.dmg`, cross-platform paths,
  and offline profiles.
