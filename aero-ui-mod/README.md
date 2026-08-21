# Aero UI (hard-lock mod)

A tiny **client-side Fabric mod** that bundles the Nostalgia Launcher's Aero glass
UI resource pack (`resourcepacks/aero-ui/`) and **hard-locks** it two ways:

1. **Always on, can't be turned off** — registered as
   `ResourcePackActivationType.ALWAYS_ENABLED`, so the pack is always enabled and
   the remove arrow can't take it out of the in-game resource-pack menu.
2. **Top priority, can't be overridden** — a Mixin into `PackRepository`
   (`rebuildSelected`) pushes the Aero pack to the **end of the selected list**
   every time packs are rebuilt. Minecraft applies selected packs last-wins, so
   the tail always wins — even against a pack the player adds on top or another
   `Position.TOP` pack. The reorder is idempotent, so dragging/reordering in the
   menu can't defeat it.

Together that's the full "hard lock" a plain resource pack can't do; the
launcher's per-launch re-enable is the "soft lock" that works on every version
including 1.12.2 Forge.

- Entry point: `src/client/java/com/nostalgia/aeroui/AeroUiClient.java`
- Top-priority Mixin: `src/client/java/com/nostalgia/aeroui/mixin/PackRepositoryMixin.java`
  (config: `src/client/resources/aero-ui.mixins.json`, wired in `fabric.mod.json`)
- Bundled pack: `src/main/resources/resourcepacks/aero-ui/` (kept in sync with
  `nostalgia/ui/assets/aero-pack/` by `aero-ui/build_pack.py`)

### Version scope of the Mixin

The Mixin targets `PackRepository.rebuildSelected(Collection)` and `Pack.getId()`
— names verified against the official 1.21.11 mappings and stable across the
**1.21.x** line the jar declares (`minecraft: ">=1.21"`). Bumping to a different
Minecraft **major** (1.20 and earlier used different names, e.g. `getName()`) may
require adjusting the injection target. Loom writes an intermediary refmap, so one
jar still covers all 1.21.x that share those intermediary names.

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
