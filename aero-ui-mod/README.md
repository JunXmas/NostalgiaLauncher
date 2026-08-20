# Aero UI (hard-lock mod)

A tiny **client-side Fabric mod** that bundles the Nostalgia Launcher's Aero glass
UI resource pack (`resourcepacks/aero-ui/`) and registers it as
`ResourcePackActivationType.ALWAYS_ENABLED` — so on modern (Fabric) instances the
pack is **always on and can't be turned off** in the in-game resource-pack menu.
This is the "hard lock" a plain resource pack can't do; the launcher's per-launch
re-enable is the "soft lock" that works on every version including 1.12.2 Forge.

- Entry point: `src/client/java/com/nostalgia/aeroui/AeroUiClient.java`
- Bundled pack: `src/main/resources/resourcepacks/aero-ui/` (kept in sync with
  `nostalgia/ui/assets/aero-pack/` by `aero-ui/build_pack.py`)

## Build

```bash
./gradlew build          # -> build/libs/aero-ui-1.0.0.jar
```

CI builds it on every change to `aero-ui-mod/` (see
`.github/workflows/build-aero-mod.yml`) and uploads the jar as an artifact.

## Toolchain note

The versions in `gradle.properties` must form a **compatible Fabric set** for the
target Minecraft version — loom's mapping base (official vs intermediary) has to
match the Fabric API build's access-widener namespace, or Loom fails at
"Failed to setup Minecraft … Expected official namespace … found intermediary".
Pin `loom_version` / `fabric_api_version` to a set that matches the target MC
(and the Gradle wrapper version) before building.
