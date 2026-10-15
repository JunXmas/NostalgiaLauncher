# Forgotten Worlds resource-pack retry

Client-only helper for Minecraft 1.21.11. On the configured server, explicitly
running `/rp`, `/goi`, `/bangtin pack`, or `/sidebar pack` sets the current
connection's resource-pack choice to **Prompt** before sending the command.
Vanilla then displays its normal optional Yes/No confirmation again.

This never accepts or downloads a pack on the player's behalf, marks a pack
required, changes the defaults for other servers, clears installed packs, or
saves a new decision. Vanilla saves the player's actual answer. Declining an
optional offer keeps the player connected, and another `/rp` asks again.

`config/forgotten-worlds-rp.json` is created once with the server address
`snow.pikamc.vn:25079`. Administrators can add alternate addresses to its
`servers` list. The list is read on client startup. Existing configuration is
preserved by modpack updates. No launcher update or server-side installation of
this helper is required.

The source is built with Java 21 against the pinned intermediary mappings by
`build.py --classpath ...`. The resulting JAR is checked into the adjacent
`dist` directory for reproducible pack publication on CI, which does not need a
Minecraft build environment. Only this client helper is included in the server
modpack update; no client mod versions or Minecraft/Fabric target change.
