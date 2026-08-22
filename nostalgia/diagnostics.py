"""Turn a Minecraft crash log into advice a human can act on.

When the game exits non-zero the player only sees "exit code 1" — useless. Here we
match a few familiar signatures in the log to say the likely CAUSE and a FIX. If
nothing matches we return None and the caller shows the raw log (no wild guesses).
Messages are in English to match the codebase's source language; the caller may
wrap them for translation.
"""

from __future__ import annotations

import re

# Each row: (regex over the log, cause title, suggested fix). Checked in order —
# first match wins, so put specific/certain signatures first.
_SIGNATURES: list[tuple[str, str, str]] = [
    (r"(UnsupportedClassVersionError|class file version \d|compiled by a more recent version of the Java Runtime)",
     "Wrong Java version",
     "This game or mod needs a newer Java than the one in use. In Settings, clear the "
     "manual Java path so Nostalgia downloads the right Java for this version."),
    (r"(java\.lang\.OutOfMemoryError|Java heap space|GC overhead limit exceeded)",
     "Out of memory (RAM)",
     "The game ran out of the RAM it was given. Raise RAM in Settings (but don't overdo "
     "it — too much also causes stutter) and close other heavy apps."),
    (r"(Missing or unsupported mandatory dependencies|requires .*fabric|Fabric API|"
     r"requires \{fabric|net\.fabricmc\.loader\.impl\.FormattedException.*depend)",
     "Missing a required mod",
     "A mod needs another mod to run (most often Fabric API). Install the missing mod — "
     "usually 'Fabric API' — for the right game version and try again."),
    (r"(Duplicate mod|found a duplicate mod|duplicate mods)",
     "Duplicate mods",
     "Two copies of the same mod are in the mods folder. Open Mods and remove the duplicate."),
    (r"(Mixin apply.*failed|MixinApplyError|InvalidMixinException|mixin.*could not|"
     r"Mixin transformation of .* failed)",
     "Mod conflict (mixin)",
     "A mod clashes with the game/loader or another mod. Remove the mod you added most "
     "recently (or one that doesn't fit this version) and try again."),
    (r"(requires minecraft version|is built for|was designed for MC|"
     r"is not compatible with|Incompatible mod set|requires loader version)",
     "Mod for the wrong game/loader version",
     "A mod isn't made for this Minecraft version or loader (Fabric/Forge/NeoForge). "
     "Replace it with the build that matches this version."),
    (r"(Failed to create window|GLFW error|Couldn't set pixel format|"
     r"Pixel format not accelerated|OpenGL 3\.2|No OpenGL context|Reason: WGL|"
     r"Failed to initialize GLFW)",
     "Graphics problem (OpenGL)",
     "The game couldn't open its window — usually a GPU driver issue. Update your graphics "
     "driver; a virtual machine or very old GPU may not support enough OpenGL."),
    (r"(Forge Mod Loader has found a problem|Forge could not initialize|"
     r"caused by mod|A potential solution has been determined)",
     "A Forge mod failed",
     "Forge reports a mod is at fault. Look for the 'caused by' line in the log to see "
     "which mod, then remove or replace it."),
]

# Log lines worth surfacing (the tail is usually the root of the crash).
_INTEREST = re.compile(
    r"(Exception|Error|Caused by|at net\.|Mixin|dependenc|OutOfMemory|GLFW|OpenGL|"
    r"Failed|crash)", re.IGNORECASE)


def diagnose(log_text: str) -> tuple[str, str] | None:
    """Return (title, fix) if a familiar failure is recognised; None otherwise."""
    for pattern, title, fix in _SIGNATURES:
        if re.search(pattern, log_text, re.IGNORECASE):
            return title, fix
    return None


def log_tail(log_lines: list[str], *, max_lines: int = 40) -> str:
    """Last few dozen lines, favouring the ones that look error-related — to share."""
    if not log_lines:
        return ""
    tail = log_lines[-200:]
    interesting = [ln for ln in tail if _INTEREST.search(ln)]
    chosen = interesting[-max_lines:] if len(interesting) >= 8 else tail[-max_lines:]
    return "".join(chosen).rstrip()


def report(message: str, log_lines: list[str], *, context: str = "") -> tuple[str, str]:
    """Build (headline, body) for the crash dialog.

    headline: one line naming the cause (or the original message if unknown).
    body: cause + fix + a log tail the player can read or copy for help.
    """
    text = "".join(log_lines)
    hit = diagnose(text)
    tail = log_tail(log_lines)
    parts: list[str] = []
    if hit:
        title, fix = hit
        headline = title
        parts.append(f"● Likely cause: {title}")
        parts.append(f"● How to fix: {fix}")
    else:
        headline = message or "The game exited unexpectedly"
        parts.append(f"● {message or 'The game exited unexpectedly.'}")
        parts.append("● Couldn't pin down the cause automatically — the log tail below may "
                     "help; paste it into Discord/a forum to ask for help.")
    if context:
        parts.append(f"● {context}")
    if tail:
        parts.append("\n— Log tail —\n" + tail)
    return headline, "\n".join(parts)
