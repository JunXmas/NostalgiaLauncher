# Changelog

All notable changes to Nostalgia Launcher, newest first.

## 0.7.6
- **Fixed: "Open folder", links and the installer opener did nothing in the
  installed app.** In the packaged build, the buttons that open a folder (Mods,
  Resource Packs, Shaders, Game folder), the Discord and sign-in links, and the
  "open the downloaded update" step all launched a helper that inherited the
  app's bundled library path and crashed on the spot — so nothing happened, with
  no error. These now launch with a clean environment, so they open reliably.

## 0.7.5
- **Fixed: the launcher could point at a game folder that no longer exists.**
  If your configured game folder had been deleted or lived somewhere temporary
  that the system wipes on reboot, PLAY aimed at an empty store and the game
  wouldn't launch, with no clear reason. The launcher now detects that on start
  and falls back to the default game folder — where your instances, versions and
  Java runtime normally live — so it keeps working instead of failing silently.

## 0.7.4
- **Continue playing.** The Home page swaps the old news feed for a
  Continue playing card: your recent single-player worlds and saved
  servers, newest first, with total play time in the header. Servers show
  their real icon and live MOTD and player count (pulled with a quick
  server ping), just like the in-game list.
- **Click to jump back in.** Clicking a world or server asks to confirm,
  then launches that instance and drops you straight into the world or
  server via Minecraft Quick Play (on 1.20+).
- **Nicer glass.** The Aero panes are clearer and softer, with a crisper
  top edge, a bottom reflection, and small glass chips that read as convex.

## 0.7.3
- **The installed app now wears the leaf logo.** The Windows, macOS and
  Linux packages previously shipped a generic glass-ball icon; they now use
  the launcher's own leaf-block logo everywhere — taskbar, dock, desktop
  shortcut and installer.

## 0.7.2
- **Draw your own skin in the launcher.** A new *Draw skin* tile on the
  Skins page opens a full pixel editor: paint the 64×64 map with pencil,
  eraser, fill and eyedropper, a colour palette plus a custom-colour
  picker, undo/redo, a grid and per-part guides, and a live rotatable 3D
  preview. Saving applies it like any other skin change.
- **Brighter, glossier sidebar.** The navigation icons are now full-colour
  Aero-style icons that light up on hover, and the selected item sits in a
  glowing accent pill so you always see where you are.

## 0.7.1
- **Fixed: updating could wipe your instance list.** Settings and instance
  data are now written atomically, so an update restarting the app mid-save
  can no longer leave the file empty (which made instances vanish and worlds
  look deleted). Instance data also loads defensively across versions. Your
  worlds were never actually deleted — they stay in your game folder.

## 0.7.0
- **One-click optimized instances.** Pick a Minecraft version and get a
  ready-to-play instance with the optimization stack already installed —
  **Fabulously Optimized** on modern versions, **MAX FPS: Optimized** on
  1.12.2. Choose it from *New Instance* or straight from the version dropdown
  next to PLAY, no setup, best FPS out of the box.
- **Your language.** Settings now has a language picker — **Tiếng Việt** plus
  Spanish, French, German, Portuguese, Russian, Chinese, Japanese and Korean.
  It switches instantly, no restart.
- **A livelier Home.** Your instances now fill a grid (many at a glance), each
  showing its modpack's icon or a grass-block default; you can set a custom
  icon per instance in its settings. Your account avatar is your skin's face,
  there's a new leaf logo, and a Discord link sits in the sidebar.
- **Browse modpacks like Modrinth** — the modpack page is now a gallery of
  cards with big preview screenshots.
- **Fixed:** installing a Forge modpack no longer looks frozen — it shows what
  the installer is doing and can't hang forever.

## 0.6.0
- **A real skin manager.** Change your skin right in the launcher, keep your
  last five skins as history that follows your **account** (not just this PC),
  pick from the default skins, toggle Classic/Slim, and spin a **3D preview**
  of your character.
- **Capes.** Microsoft accounts can view and wear their Mojang capes in-app;
  the cape shows on the 3D model too.
- **Everyone sees everyone's skins — even offline.** The launcher runs a small
  skin service and auto-installs CustomSkinLoader when you make a modded
  instance or a modpack, so players using Nostalgia see each other's custom
  skins on any server, offline profiles included.
- **Modpack icons** now appear on the Home instance cards instead of a plain
  cube.

## 0.5.0
- **Sign in with Microsoft just works.** The launcher now ships with its own
  approved Microsoft application, so you no longer have to create and paste an
  Azure client ID — click sign in and go. (You can still override it with your
  own ID in Settings or the `MC_CLIENT_ID` environment variable.)
- **Fixed: creating a legacy instance (e.g. Forge 1.12.2) failed.** Older
  Minecraft versions could crash mid-download or the Forge installer would give
  up on a dropped connection. Asset downloads are now de-duplicated and retried,
  the loader installer retries too, and a truncated version file re-downloads
  itself instead of erroring out.

## 0.4.0
- **The whole UI feels alive now.** Every button lifts, glows and casts a
  softer shadow as you hover — as if floating up to be pressed — and sinks
  when you click. Sidebar items slide and brighten, the tab underline glides
  between tabs, and list rows fade in instead of snapping.
- **Learn by doing, not by reading.** The home screen drops the text hints:
  a clear **＋** card is the obvious way to make an instance, and resting on
  an instance dims it and shows a ▶ so it plainly says "click to play". The
  instance you'll launch shows first.
- **A cleaner way to pick a loader.** Making an instance now opens a tidy
  centred *Choose a loader* card — Vanilla, Fabric, Forge, NeoForge — each
  with a colour and a one-line description, instead of a stray menu.
- **Browse modpacks like on Modrinth.** GET MODPACK opens a full page with a
  category filter, a game-version box, sort options, and rich cards showing
  the icon, author, description, downloads, followers and tags. Click a card
  to install it as a new instance.
- **Fixed: Back / Edit / Play did nothing on an instance page** — the window
  drag strip was swallowing the clicks. The header moved down so the buttons
  work and no longer crowd the window controls.

## 0.3.0
- **Cleaner, Modrinth-style layout.** Clicking an instance now opens its own
  page with a header (Play/Stop, Edit, play time) and tabs for **Mods,
  Resource Packs, Shaders and Logs** — everything for that instance in one
  place. The sidebar loses the global content tabs, all still in Aero glass.
- **Modpack installs show a progress bar** and download files in parallel, so
  a big pack installs fast instead of looking stuck.
- Trimmed redundant buttons and the duplicated home shortcuts.

## 0.2.9
- **One-click mod updates.** The Installed tab flags mods with a newer Modrinth
  build (matching your instance) and adds an *Update all* button.
- **Dependency resolution.** Installing a mod now pulls in its required
  dependencies automatically, so things like Fabric API just come along.
- **Shaders** are now a first-class content type — browse and install shader
  packs from Modrinth like mods and resource packs.
- **Per-instance settings**: rename an instance and override its memory (RAM)
  and Java path; **Duplicate** and **Repair** buttons too.
- **In-app log viewer** — a LOGS button opens the live game log without leaving
  the launcher.
- Instances now track **play time and last-played**.

## 0.2.8
- **Pick a loader when you make an instance** — Vanilla, Fabric, Forge or
  NeoForge. Forge/NeoForge run their official installer for you.
- **Install modpacks straight from Modrinth.** GET MODPACK on the Instances
  page downloads a pack and sets it up as a ready-to-play instance.
- **PLAY becomes STOP while the game is running** — one click closes the game,
  and it flips back to PLAY when the game exits.
- **A nicer version picker**: a centered dialog with a live filter box, an
  *Include snapshots* toggle, and a "downloaded" marker.
- Updates now install and **restart on their own** — no more "restart?" prompt.
- Mods you install match the exact instance you're installing into.

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
