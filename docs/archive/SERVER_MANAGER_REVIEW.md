# Server manager preview — 2026-10-07

This is source review on `preview/glass-review`, version still 1.2.0rc8. No installer, version bump, tag, draft release or production deployment was created. Screenshots are supplied separately in chat and excluded from release assets.

## Behavior

The Bản chơi workspace now contains a second Server tab instead of adding another sidebar destination. A centered mica dialog installs a pinned official server build. The manager separates configuration, content, console and advanced files. Lists and forms use the existing inertial scrolling component; small windows retain scrolling and fixed actions.

Delete confirmation is a modal Overlay popup above the instance/server manager. Cancel and Escape preserve the manager. Accept invokes the action once. Instance deletion retains its existing trash/recovery behavior; server deletion moves the complete server directory, including worlds, to `servers/.trash`.

| Name | Duration | Price | Local server management |
| --- | --- | --- | --- |
| Plus | 1 month | 29,000 VND | No |
| Pro | 6 months | 69,000 VND | Yes |
| Max | 1 year | 109,000 VND | Yes |
| Ultimate | Lifetime | 209,000 VND | Yes |

Existing offer IDs, durations and prices remain unchanged. Server management runs on the host computer and does not include a VPS. Release runtime passes `plus_enabled=False`; the account service also defaults both Plus and server hosting off. Screenshots use a controlled Pro account/catalog fixture to review otherwise-disabled paid UI. Production Google configuration/deployment and payment setup are still pending.

## Engines and content

The installer supports Paper, Purpur, Folia, Fabric, Vanilla and Arclight Forge/NeoForge/Fabric hybrid engines through official catalogs. Game/build selection is pinned, downloads bounded and checksummed when the vendor supplies a digest, and local SHA256 is verified before launch. Fabric's executable-jar endpoint supplies no vendor digest; it uses official HTTPS followed by a stored local SHA256. Purpur exposes MD5; a local SHA256 is also stored.

Paper selects stable builds. Official Folia builds can be Alpha and are labeled accordingly. Folia plugins must explicitly declare root `folia-supported: true` in their JAR descriptor. Hybrid plugin search uses Bukkit/Spigot compatibility rather than assuming Paper APIs.

Modrinth filters server-side content by exact Minecraft version and engine loader, resolves required dependencies and commits the batch after authorization. Legacy v2 plugin projects marked as `mod` are accepted only with matching plugin loaders and version filters. Hangar selects direct Release downloads for Paper/Purpur/Folia; external downloads and required manual dependencies are excluded. Existing manually copied JARs are discovered, preserved and not silently overwritten. Removal moves content to `.nostalgia/removed`.

Configuration includes MOTD, port, player cap, view/simulation distance, spawn protection, difficulty, game mode, PvP, whitelist, online account verification, RAM, custom/automatic Java and explicit EULA acceptance. The properties editor retains custom keys/comments and decodes escaped Java property values. Advanced file editing is bounded and rejects traversal/symlinks, metadata files and world/library scans. Content/settings changes require the managed server to be stopped. Normal stop sends the Minecraft `stop` command before termination fallback.

## Account boundary and multiplayer

Backend authorization checks the active Google session and D1 membership on every server request. Client tier/payment claims do not grant access. Atomic D1 run records allow one active run/account, with a 120-second lease renewed every 25 seconds outside the UI thread. Expiry, revoked membership and session rotation are covered by backend tests.

The dedicated server can explicitly open the existing friends relay only after its own console reports readiness. Its verified port is supplied to the relay. Invitations become available once hosting is ready; stopping the server closes the associated room. Mod/hybrid clients still need a compatible client modpack. This does not claim automatic dedicated-server-to-client pack conversion or cross-loader compatibility.

Public Java server binaries can be run outside the launcher. This protects backend authorization and managed flows, but cannot provide an unbypassable local-server paywall. The existing free LAN relay cannot authenticate whether a port originates from integrated LAN or a dedicated server; it is not an exclusive paid relay.

## Validation

- Full client suite before the final vendor/visual corrections: **1,454 passed, 7 skipped, 1 deselected**.
- Final core/vendor/configuration/architecture/convention checks: **27 passed**.
- Final native Qt/OpenGL server, instance, confirmation and payment-plan checks: **13 passed**.
- Full backend workerd/D1 suite: **26 passed**.
- Ruff clean; mypy clean for **273 source files**; whitespace and dependency-lock checks clean.
- Nine actual Qt/OpenGL screenshots: workspace, hybrid installer, settings, plugin library, version picker, server deletion, 1024×600 at 150% font size, plans and instance deletion. No QML warnings were captured. These are controlled fixtures, not live paid accounts.

Real official downloads, real Java 21 processes and real world creation/saving were checked through the new manager:

| Engine | Minecraft | Build | Ready / saved world |
| --- | --- | --- | --- |
| Paper | 1.21.1 | 133 | Yes / Yes |
| Purpur | 1.21.1 | 2329 | Yes / Yes |
| Fabric | 1.21.1 | 0.19.5 | Yes / Yes |
| Folia | 1.21.4 | Alpha 6 | Yes / Yes |
| Arclight Fabric | 1.21.1 | 1.0.1-8ec9529 | Yes / Yes |
| Arclight NeoForge | 1.21.1 | 1.0.1-8ec9529 | Yes / Yes |
| Vanilla | 1.21.1 | 1.21.1 | Yes / Yes |

Arclight Forge 1.21.1 build 1.0.1-8ec9529 failed before readiness with an upstream `MinecraftServerMixin` InvalidInjectionException on a clean world. Its exact published SHA256 is excluded from the catalog; the UI explains using another version or NeoForge/Fabric. The failed build is not reported as working.

Real LuckPerms files were downloaded and checksum-verified through Modrinth for Paper and Folia; the Folia descriptor check passed. ViaVersion 5.12.0 was downloaded and SHA256-verified through Hangar after filtering 25 compatible Release versions.

Live server checks use a test account gateway and the environment network proxy, not a deployed Google service. They verify startup and world saving, not joining from another physical computer, long multiplayer sessions, arbitrary plugin/mod combinations, production Google OAuth or Windows/macOS execution. Those remain release acceptance checks.
