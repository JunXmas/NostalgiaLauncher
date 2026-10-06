# Minecraft block assets

Model JSON and PNG textures copied unchanged from the official Minecraft Java 1.20.1 client.
Copyright Mojang Studios / Microsoft. These assets retain their original ownership.

Source: https://piston-data.mojang.com/v1/objects/0c3ec587af28e5a785c0b4a7b8a30f9a8f78f838/client.jar

Client SHA-1: `0c3ec587af28e5a785c0b4a7b8a30f9a8f78f838`

Includes the UI blocks (grass, crafting table, bookshelf, diamond block, command block,
barrel, redstone block, beacon), home scene blocks (oak log/leaves, dirt, stone, glowstone),
parent models, referenced textures, and grass/foliage biome colormaps. `source.json`
records SHA-256 for every copied file. PNGs and model JSON are copied without edits.

The Log icon uses the vanilla barrel model. Minecraft Java chests use an entity renderer;
a plain textured cube is not a faithful chest, so no invented chest cube is used.

The adjacent `../home-island.png` is a derived UI render composed by
`nostalgia.ui.home_scene` using these original models/textures and plains biome tint.
It is not an in-game screenshot or an unchanged Mojang PNG. The original model geometry,
UVs and texture files are preserved; scene placement and UI lighting belong to the preview.
