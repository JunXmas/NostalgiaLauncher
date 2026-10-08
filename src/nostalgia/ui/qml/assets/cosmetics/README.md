# Nostalgia profile cosmetics

Original artwork generated for the approved Nostalgia profile concepts. These
are avatar overlays and profile backgrounds, not Minecraft block or skin models.

| Display name | Existing service ID | Asset prefix |
| --- | --- | --- |
| Amethyst | `amethyst` | `amethyst` |
| Grove | `emerald` | `grove` |
| Eclipse | `amber` | `eclipse` |

Frames have genuine alpha transparency in the center and around the ornament.
QML bounds their decoded size to 384 px and banners to 1536 px, loads them
asynchronously, shares the image cache and clears sources when hidden. Only
pointer interactions animate; there are no continuous animation loops.

The existing backend profile entitlement controls applying a set. Browsing a
locked set changes the local preview only. Artwork distributed with a desktop
client is extractable; authorization protects saved and shared profile state.

The QML asset directory is included by the existing packaging specification.
Review screenshots are kept outside the repository and release assets.

Definitions and lifecycle now come from `social/cosmetics.json`. See
[`docs/COSMETIC_MAINTENANCE.md`](../../../../../../docs/COSMETIC_MAINTENANCE.md)
for adding artwork, retiring sets, disabling sets and synchronizing backend validation.
