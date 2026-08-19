<div align="center">

# 🪟 Nostalgia Launcher

### The Minecraft launcher that remembers when things felt magic.

Frosted Aero glass, a warm little home screen, and everything that should *just work* —
hand-built from scratch in Python, for everyone who misses the good old days.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6%20(Qt)-41CD52?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-blue)
![Windows](https://img.shields.io/badge/Windows-.exe-0078D6?logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-.dmg-000000?logo=apple&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-.deb-FCC624?logo=linux&logoColor=black)

![Nostalgia Launcher](docs/screenshot.png)

**[⬇️ Download the latest release](https://github.com/JunXmas/NostalgiaLauncher/releases/latest)**

</div>

---

## Remember?

Remember when a computer glowed like glass, and opening a program felt like a tiny event?
Remember loading up Minecraft after school — no launchers to configure, no modpacks to
debug, just *you and a blocky sunset*?

That feeling went somewhere. **Nostalgia Launcher** is my attempt to bring it back.

Every panel here is real frosted **Aero glass**, drawn by hand, floating over a background
you can make your own. Under that glossy surface is a launcher that quietly does the hard
parts for you — so you can skip the setup and get straight to the part you actually came for:
**playing.**

It's my very first real project, so you might still find a rough edge here and there. But it
already does the important things beautifully, and I'd love for you to try it. Welcome back 💙

---

## What makes it special

### 🪟 It actually *looks* like Aero
Not a flat "glassmorphism" box — the real recipe: a blurred backdrop, a blue tint, fine acrylic
noise, and a glossy top sheen with real depth. Buttons lift as you hover and **sink with a little
weight** when you press them. It runs the effect itself, so it looks like true frosted glass on
*any* machine — even a Linux desktop whose compositor can't blur.

### 🎮 One click, and you're in
Pick a version and press **Play**. That's it. No file hunting, no Java to install, no wiki tabs.
Vanilla, **Fabric, Forge and NeoForge** are each a single click.

### ⚡ Best FPS, out of the box
Choose *Optimized* and the launcher builds you a ready-to-play instance with the whole speed
stack already inside — **Fabulously Optimized** on modern versions, **MAX FPS: Optimized** on
1.12.2. No mods to research. It just runs smooth.

### 📦 Separate worlds that never collide
Every instance is its own little universe — its own mods, saves and config — while the heavy
shared stuff stays shared, so instances are cheap. Keep a pure survival world, a chaos modpack,
and your beloved 1.12.2 side by side, and **none of them can ever break another.**

### 🧩 A mod shop that lives inside the launcher
Search [Modrinth](https://modrinth.com) right from the Mods, Resource Packs and Shaders tabs —
one click installs, and it even **pulls in required dependencies for you**. Flip any mod on or
off without deleting it, spot which ones have updates and **update them all at once**, or browse
**modpacks** as a gallery of big preview cards, Modrinth-style.

### 🎨 Draw your own skin — right here
This is the part no other launcher gives you. Open the **skin editor** and paint your character
pixel by pixel — pencil, fill, eyedropper, undo/redo, per-part guides — while a **live 3D model
turns beside you**. Change your skin, keep a history of your last five, toggle Classic/Slim, and
if you're signed in with Microsoft, **wear your cape** on the 3D preview too.

### 👀 Everyone sees everyone's skin — even offline
On most launchers your custom skin is invisible to friends on cracked or offline servers.
Nostalgia runs a tiny skin service and sets things up automatically, so **players using Nostalgia
see each other's skins on any server** — offline profiles included.

### ↩️ Jump back in with one tap
Your home screen remembers where you left off: your **recent worlds and servers**, your **total
play time**, and for each server its **real icon, live description and player count**. Tap one,
confirm, and the launcher opens that instance and drops you **straight into the world or server.**

### 🌍 Made to feel like home
Full **Tiếng Việt** and nine more languages, switching instantly with no restart. Any image can be
your background. Signing in with Microsoft **just works** — no client ID to create, no keys to
paste; add one account or several and hop between them freely. Don't own the game yet? It launches
the official **Demo** automatically.

### 🛟 Quietly looking after you
Java installs itself, matched to each version. Updates arrive on their own. A one-click **Doctor**
tells you exactly what's missing *before* you launch — no cryptic Java stack traces — and your
instance list is written safely, so an update can never wipe your worlds.

---

## A look inside

| Home | Instances | Settings |
|:---:|:---:|:---:|
| ![Home](docs/screenshot.png) | ![Instances](docs/screenshot-installations.png) | ![Settings](docs/screenshot-settings.png) |

---

## Get it

**The easy way** — grab a real installer from the
**[Releases page](https://github.com/JunXmas/NostalgiaLauncher/releases/latest)**:
Windows `.exe`, macOS `.dmg`, and Linux (Mint/Ubuntu/Debian) `.deb`, all built by GitHub Actions.
On Windows and macOS the first launch needs one click past the OS warning unless the build is
code-signed — [docs/PACKAGING.md](docs/PACKAGING.md) explains exactly which one.

**From source** — on any of the three platforms:

```bash
pip install -r requirements.txt      # PySide6 + requests
python -m nostalgia gui
```

**From the command line**, if that's your thing:

```bash
python -m nostalgia fabric 1.21.4     # install Fabric
python -m nostalgia jre 1.21.4        # pre-fetch Java
python -m nostalgia doctor 1.21.4     # health-check an install
```

> **Signing in:** the launcher ships with its own Microsoft-approved app, so you just click and
> go. Prefer your own? Drop an Azure client ID into Settings or the `MC_CLIENT_ID` environment
> variable and it'll use that instead — nobody's ID is baked in where you can't change it.

---

## How it's built

Pure Python + PySide6 (Qt), no game code borrowed. A few pieces I'm quietly proud of:

- **The glass** (`ui/`) samples a blurred copy of the window's own background, so it looks like
  real frosted glass everywhere — even where the desktop itself can't blur.
- **`jre.py`** pulls Mojang's own Java runtimes, matched per version — no manual setup, ever.
- **`skins.py`** + a small backend let offline players see each other's custom skins, with
  CustomSkinLoader wired up for you automatically.
- **`identity.py`** gives each player a stable ID that survives switching from an offline profile
  to a premium account, and can follow you across machines.
- **`doctor.py`** inspects every link in the chain — jars, libraries, natives, assets, Java, the
  final command — so problems are obvious, not mysterious.

---

## Credits & license

Released under **GPL-3.0** — use it, learn from it, build on it; just keep it open and credit back.

Huge thanks to [PrismLauncher](https://github.com/PrismLauncher/PrismLauncher) — I studied how it
handles offline profiles and ownership, then wrote my own version in Python (no code copied). The
Microsoft sign-in flow follows the public docs at
[minecraft.wiki](https://minecraft.wiki/w/Microsoft_authentication).

<div align="center">

*Not affiliated with or endorsed by Mojang or Microsoft.*
**Made with love, a lot of late nights, and a little bit of longing for the way things used to be.**

</div>
