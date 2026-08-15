<div align="center">

# 🪟 Nostalgia Launcher

**A Minecraft: Java Edition launcher written in Python, styled after the Windows Vista/7 Aero glass look.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6%20(Qt)-41CD52?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-blue)
![Status](https://img.shields.io/badge/status-work%20in%20progress-orange)

![Nostalgia Launcher screenshot](docs/screenshot.png)

*My very first project — still unfinished, so expect some bugs. Thanks for stopping by 💙*

</div>

---

## ✨ Features

- 🎮 **Vanilla and Fabric** — download any version from Mojang's servers, install the Fabric loader in one click
- 👤 **Multiple accounts** — sign in with Microsoft right inside the app, switch without re-logging in
- ☕ **Automatic Java** — downloads the right JRE for each version, no manual Java install
- 📰 **News & patch notes** — pulled straight from the official launcher's sources
- 🧪 **Diagnostics tool** — inspects every link in the install so you know exactly what's broken
- 🪟 **Real Aero glass** — frosted blur, specular border, top highlight, double drop shadow, hand-drawn with QPainter

## 🖼️ Screenshots

| Installations | Settings |
|:---:|:---:|
| ![Installations](docs/screenshot-installations.png) | ![Settings](docs/screenshot-settings.png) |

## 🚀 Getting started

```bash
# 1. Install dependencies
pip install -r requirements.txt      # needs PySide6-Essentials and requests

# 2. Open the GUI
python -m nostalgia gui

# or use the command line
python -m nostalgia versions --limit 10
python -m nostalgia fabric 1.21.4          # install Fabric
python -m nostalgia jre 1.21.4             # pre-download Java
python -m nostalgia doctor 1.21.4 --hashes # check an installation
```

Microsoft sign-in needs a free Azure application (Personal accounts, with *Allow
public client flows* enabled), then `export MC_CLIENT_ID=<client-id>`. See
[Microsoft sign-in](#-microsoft-sign-in) below.

## 👥 Account types

| Account type | How it runs |
|---|---|
| Microsoft, owns the game | Full game, can join online servers |
| Microsoft, doesn't own the game | Official demo mode (fixed world, ~100 minutes) |
| Owns it but currently offline | Full game from the cached session (singleplayer/LAN) |
| Offline profile | Full game offline — only unlocked once the launcher has a game-owning account |

Offline profiles follow [PrismLauncher](https://github.com/PrismLauncher/PrismLauncher)'s
model: gated on two levels — you can't add one until a game-owning account
exists, and they drop to demo mode if that account is removed.

## 🔑 Microsoft sign-in

1. https://portal.azure.com → **App registrations** → *New registration*
2. Supported account types: **Personal Microsoft accounts only**, leave Redirect URI empty
3. **Authentication** → *Advanced settings* → **Allow public client flows: Yes**
4. Copy the *Application (client) ID* → `export MC_CLIENT_ID=<id>`
5. New apps must request Minecraft API access at https://aka.ms/mce-reviewappid —
   until approved, sign-in runs all the way to the last step and then returns 403.

## 🧩 Structure

| File | Role |
|---|---|
| `auth.py` | Microsoft device code → Xbox Live → XSTS → Minecraft Services |
| `accounts.py` | `AccountStore`, ownership gate, offline UUID v3 |
| `identity.py` | Stable `player_id`, groups multiple accounts, Google linking |
| `install.py` | Version manifest, client.jar, libraries, natives, assets; SHA1 checks |
| `fabric.py` | Fabric meta, maven path building, `inheritsFrom` merging |
| `jre.py` | Auto-downloads Mojang's JRE per `javaVersion.component` |
| `launch.py` | Rule evaluation, `${...}` substitution, Java selection, process launch |
| `doctor.py` | Diagnoses each install link (no account needed) |
| `content.py` | News and patch notes from Mojang, cached |
| `ui/` | Aero interface: `theme` · `glass` · `hero` · `widgets` · `controls` · `menus` · `dialogs` · `pages` · `window` · `worker` · `app` |

## 📝 Technical notes

<details>
<summary><b>Hand-drawn Aero glass</b></summary>

Instead of asking the compositor to blur the desktop behind the window (KWin can,
Cinnamon/Mint can't), each glass panel samples a pre-blurred copy of the window's
own hero image — visually identical, and it behaves the same on every machine.
Four layers: blurred backdrop, cool blue tint, top highlight, two-step bevel;
plus a focus halo and double drop shadow on the outer frame.
</details>

<details>
<summary><b>Fabric: merging <code>inheritsFrom</code></b></summary>

Fabric meta only returns the delta from vanilla. Three easy mistakes when merging:
loader libraries must come <b>before</b> vanilla on the classpath; Fabric only
gives maven coordinates so the path has to be built by hand; the Fabric profile
reuses the vanilla jar, so it must not be duplicated.
</details>

<details>
<summary><b>Automatic Java</b></summary>

Each version declares a <code>javaVersion.component</code> (jre-legacy = Java 8,
gamma = 17, delta = 21). Mojang hosts the matching runtime per OS; the launcher
downloads it into <code>~/.nostalgia-launcher/runtime/</code> on demand. Java
selection order: custom path → downloaded JRE → system Java.
</details>

<details>
<summary><b>Identity that survives going premium</b></summary>

Offline UUIDs are derived from the username; premium UUIDs are assigned by Mojang —
two different values. <code>identity.py</code> mints a separate
<code>player_id</code> (uuid4, not derived from any UUID) so player data survives
the offline → premium switch. Google linking is an external key attached to that
identity.
</details>

## 📜 License & credits

Released under **GPL-3.0** — free to use, modify and share, as long as derivatives
stay open-source and keep attribution.

Thanks to [PrismLauncher](https://github.com/PrismLauncher/PrismLauncher) (GPL-3.0):
the ownership-gate model and offline UUID scheme were referenced from Prism's
*behaviour* — all code here is independently written in Python, not copied from
their source. The authentication chain is based on public protocol docs at
[minecraft.wiki](https://minecraft.wiki/w/Microsoft_authentication).

*Not affiliated with or endorsed by Mojang / Microsoft.*
