## Nostalgia Launcher 1.0.1

A small polish release on top of 1.0:

- **Sharper home screen.** The hero image now ships at its full 2528 px, adaptively sharpened,
  and is drawn with mipmaps — about twice the edge detail at display size.
- **Continue playing** (already in the final 1.0 build): your most recent worlds across all
  instances as Minecraft-style block buttons; one click launches the instance straight into that
  world (quick play, Minecraft 1.20+).
- CI flake in the modpack-import test fixed.

Downloads and platform notes are the same as 1.0 below. If you run 1.0.0 on Linux or Windows,
the launcher will offer this update by itself.

---

## Nostalgia Launcher 1.0 — the rework

The first release of the from-scratch rewrite of Nostalgia Launcher. Same name, same heart,
none of the old code: 130 commits, 770 tests, one façade between the UI and the engine, and a
rule that nothing ships without a test.

### What's new compared to the old NostalgiaLauncher

- **Accounts**: Microsoft, **Ely.by** (authlib-injector verified by SHA-256) and offline, side by side.
- **Instances**: Vanilla, Fabric, **Quilt**, Forge, NeoForge and an **Optimized** preset; each
  instance can live in **its own folder on any disk**; per-instance play time, launches, worlds, mods.
- **Create dialog**: official key art per Minecraft generation, cards that light up and lift,
  versions sliding down as stone buttons.
- **Library**: Modrinth **and CurseForge** (no API key), modpack import by file or **drag & drop**.
- **Play together**: LAN over relay with 18-character room codes and ten tested security rules.
- **Skins**: a skin library inside the launcher; one *Thêm skin* button that uploads to Mojang
  for Microsoft accounts and applies instantly for everyone else.
- **Feedback**: live game log with filters, toasts + chimes, soft dashboard-style UI sounds,
  Discord Rich Presence (off by default).
- **Auto-update** with mandatory `SHA256SUMS` verification (Linux and Windows packages apply
  themselves; macOS shows the download page).
- **Engineering**: zero runtime dependencies in the core, 7-layer architecture with tests
  guarding the boundaries, every file ≤ 200 lines, ruff + mypy strict, CI on Python 3.12 / 3.13.

### Downloads

| Platform | File | Notes |
|---|---|---|
| Linux (any distro) | `nostalgia-<ver>-linux-x64.AppImage` | `chmod +x`, double-click. Needs glibc ≥ 2.35 (Ubuntu 22.04+, Debian 12+, Mint 21+, Fedora 36+, Arch). |
| Debian / Ubuntu / Mint / Pop!_OS | `nostalgia_<ver>_amd64.deb` | `sudo apt install ./nostalgia_<ver>_amd64.deb` |
| Fedora / openSUSE / RHEL / Nobara | `nostalgia-<ver>-1.x86_64.rpm` | `sudo dnf install ./nostalgia-<ver>-1.x86_64.rpm` |
| Linux, portable | `nostalgia-<ver>-linux-x64.tar.gz` / `.zip` | unpack, run `Nostalgia/nostalgia-ui` |
| macOS Apple Silicon | `nostalgia-<ver>-macos-arm64.dmg` | drag to Applications; first launch: right-click → Open (unsigned) |
| macOS Intel | `nostalgia-<ver>-macos-x64.dmg` | same |
| Windows 10/11 x64 | `nostalgia-<ver>-windows-x64-setup.exe` | installer, no admin needed; SmartScreen → "More info → Run anyway" (unsigned) |
| Windows, portable | `nostalgia-<ver>-windows-x64.zip` | unpack, run `Nostalgia\nostalgia-ui.exe` |

Verify any download against `SHA256SUMS`. The zips are what the built-in updater downloads.

### Not back yet

Pixel skin editor, translations (the UI is Vietnamese for now). They are coming, on top of a
codebase that can carry them.
