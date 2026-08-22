# Changelog

All notable changes to Nostalgia Launcher, newest first.

## 0.9.7
- **Cracked players now see each other's skins.** The launcher makes sure
  CustomSkinLoader (pointed at the built-in skin server) is set up on the game
  you launch — every launch, including Play Together — so offline players see
  each other's skins in-game with no setup. Your skin is shared automatically
  when you change it in the launcher. Checking is instant when it's already
  installed, and you can turn it off with `shared_skins` in the config.

## 0.9.6
- **Pick which game to launch on the Play Together page.** A "Game to launch"
  selector now sits at the top of the page and is used by both sides: Launch &
  Join starts the game you chose into your friend's room, and a new Launch & Host
  button lets you start the host game right from the page (then Esc → Open to LAN)
  — no need to go back to Home first. The selector defaults to your current game.

## 0.9.5
- **Fixed: the window could freeze for a moment when you pressed PLAY.** For
  Microsoft accounts the launcher refreshed your login on the UI thread before
  starting; on a slow connection the whole window locked up until it finished.
  That refresh now runs in the background, so PLAY responds instantly.
- **Fixed: a genuine game crash could be reported as a clean exit.** The button
  watchdog added in 0.9.4 could mask a non-zero exit code; crashes now surface
  their error again, while Stop / Alt+F4 stay quiet as before.
- **Fixed: Play Together could show "Live" even when the relay was unreachable.**
  Hosting now waits for the relay connection before saying friends can join, and
  reports an error instead of failing silently if the connection drops.
- **Fixed: some buttons stayed in English on other languages.** The PLAY/STOP
  button and every button on the Play Together page now follow your chosen
  language, and Vietnamese picked up eight labels it was still missing.

## 0.9.4
- **Fixed: PLAY button stuck on STOP after closing the game.** When Minecraft was
  closed with Alt+F4 (or Stop hit an error), the button could stay on STOP and
  never flip back to PLAY. The button now tracks the real game process, and a
  watchdog resets it within a second even if the log reader is still winding down.

## 0.9.3
- **Fixed: couldn't install resource packs or shaders from Browse Modrinth.**
  When installing into a chosen game, the launcher wrongly filtered by the mod
  loader (Fabric/Forge) — but resource packs and shaders aren't tied to a loader,
  so nothing matched and you got "no compatible version". They install correctly
  now.

## 0.9.2
- **Full translations for eight more languages.** Spanish, French, German,
  Portuguese, Russian, Chinese, Japanese and Korean now cover the whole
  interface — menus, pages, dialogs and the new Play Together page — instead of
  just a handful of labels. Pick your language in Settings.

## 0.9.1
- **Five built-in menu backgrounds.** TUT 11 Sunrise, TUT11 sunset, TUT1
  panorama, DanTDM Labs and TUT1 Village now ship with the launcher — pick any of
  them on the Theme In-Game page, no importing needed.
- The Play Together page now shows in your chosen language (its text was
  English-only before).

## 0.9.0
- **Play together — no server, no setup.** A new **Play Together** page lets you
  host your world or join a friend's with just a short room code. The host opens
  their world to LAN, shares the code, and the friend's world shows up right in
  Minecraft's LAN list — no dedicated server, no mods, no port-forwarding, and it
  works even when the two of you are on different networks.
- **The Aero look locks in across far more versions.** The launcher auto-picks a
  real hard-lock for Fabric **1.16.5, 1.17.1, 1.18.2, 1.19.4, 1.20.6 and
  1.21.11**, the newest **26.x** builds, and **Forge 1.12.2** — there the Aero
  pack can't be turned off *or* overridden by another pack. Every other version
  keeps the re-applied pack, so the theme still shows everywhere (down to 1.8.9).
- **Pick your in-game background.** The new **Theme In-Game** page shows your menu
  backgrounds as a card grid with a gently rotating live preview; click one to set
  it. Comes with distinct Day and Night scenes plus any you add, and backgrounds
  can be renamed.
- **Install to the right game, every time.** Installing a mod or resource pack now
  opens a modal to pick which game it goes into — incompatible games are dimmed
  with the reason — so nothing lands in the wrong place. The easy-to-miss corner
  dropdown is gone.
- Removed the redundant "Dark menu background" toggle from Settings (the Theme
  In-Game page covers it now).

## 0.9.0-beta.2
- **The Aero look now locks in across far more versions.** The launcher
  auto-picks a real hard-lock for Fabric **1.16.5, 1.17.1, 1.18.2, 1.19.4,
  1.20.6 and 1.21.11**, the newest **26.x** builds, and **Forge 1.12.2** — on
  those the Aero pack can't be turned off *or* overridden by another pack. Every
  other version keeps the re-applied pack, so the theme still shows everywhere
  (including 1.8.9).
- **Panorama page polish.** Backgrounds can be renamed, the Day and Night scenes
  are now distinct, and the old Home "Theme: Day/Night" button is gone — the
  Panorama page covers day, night and every custom background.

## 0.9.0-beta.1
- **Panorama backgrounds you can pick.** A new **Panorama** page shows your
  menu backgrounds as a card grid — a live preview, name, tags and an Active
  badge. Click one to set it; the launcher rebuilds the Aero pack for every
  game so the title-screen background changes on next launch (or press
  **F3+T** in-game to see it live). Comes with Day, Night and a few Aero
  panorama themes.
- **The Aero look now locks in on more versions.** The launcher picks the right
  hard-lock automatically per game: the Aero pack can't be turned off *or*
  overridden on 1.21.11 and on the newest 26.x builds, and simply shows as a
  normal (re-applied) pack everywhere else from 1.16.5 up.
- **The Aero pack loads cleanly on every version.** Its pack format is now
  matched to each game, so newer versions no longer drop it as "incompatible".
- Refreshed the built-in Day and Night title-screen panoramas.

## 0.8.0-beta.3
- **Day/night menu, one click from Home.** A "Menu: Day/Night" button on the
  dashboard flips the title-screen panorama between the daytime and nighttime
  scenes. It applies on next launch — or, in a running game, press **F3+T** at
  the title screen to see it switch live, no restart needed.
- **The Windows 7 look.** The interface now ships with Selawik (an open-source
  stand-in for Segoe UI, the Aero-era font) and a larger, easier-to-read sidebar.
- **Browse knows what you already have.** Mods already installed show an
  "Installed" tag when browsing, and won't be downloaded again.
- **Mods, Resource Packs and Shaders are back in the sidebar** (and still inside
  each game's tabs), so you can browse them either way.
- Removed the bundled FancyMenu mod (it added nothing on this version); the
  animated menu blur (Blur+) stays. Updated the Discord link.

## 0.8.0-beta.2
- **Fixed: some game versions wouldn't launch at all** (e.g. 1.21.4, 1.20.6),
  while others (like 1.21.11) worked. A Fabric game's own libraries and the
  base game's libraries could include the same library at two versions, and both
  ended up loaded at once — which the mod loader refuses, so the game quit before
  it even opened, with no error. The launcher now keeps a single version of each
  library (the loader's), matching the official launcher.

## 0.8.0-beta.1
_Beta — a big ease-of-use and looks upgrade. Please report anything odd._

- **Easier for newcomers.** A first-run welcome sets up a ready-to-play game in
  one click; menus speak plain language ("Games" instead of "Instances", with
  hover tips everywhere); the sidebar is trimmed to five task-first entries
  (mods, resource packs and shaders now live inside each game); and rarely-used
  settings (game folder, Java path) hide behind an "Advanced" toggle.
- **Safer to explore.** Removing a game now moves it to a `.trash` folder you can
  restore from, instead of deleting it outright.
- **Aero glass menus.** A frosted-glass Aero look across in-game menus (with the
  world softly blurred behind), and the animated **title-screen panorama** now
  ships in **Day** and **Night** themes — switch them under Settings.
- **Extras bundled for modern Fabric games.** Blur+ (animated menu blur) and
  FancyMenu (menu customization) install and lock in automatically alongside the
  Aero pack.
- **Fully translatable UI**, with Vietnamese included for all the new screens.

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
