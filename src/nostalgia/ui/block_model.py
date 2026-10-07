"""Đọc nguyên model JSON và texture Minecraft, kể cả chuỗi parent và tham chiếu #texture."""

from __future__ import annotations

import json
import logging
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QImage, QTransform

from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string
from nostalgia.ui.block_tint import load_biome_tint, tinted

logger = logging.getLogger(__name__)

CUBE_FACES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "front": ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)),
    "back": ((1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)),
    "right": ((1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)),
    "left": ((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)),
    "top": ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)),
    "bottom": ((-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)),
}
FACE_NAMES = {
    "south": "front",
    "north": "back",
    "east": "right",
    "west": "left",
    "up": "top",
    "down": "bottom",
}


@dataclass(frozen=True, slots=True)
class BlockSurface:
    face: str
    vertices: tuple[tuple[float, float, float], ...]
    texture: QImage
    layer: int = 1
    back_faces: bool = False


@dataclass(frozen=True, slots=True)
class BlockModel:
    surfaces: tuple[BlockSurface, ...]
    gui_rotation: tuple[float, float, float]
    gui_scale: tuple[float, float, float]


def _resource(name: str, directory: str, suffix: str) -> str:
    namespace, separator, key = name.partition(":")
    key = key if separator else namespace
    if (separator and namespace != "minecraft") or ".." in key.split("/"):
        raise ValueError("unsupported Minecraft resource")
    return f"{directory}/{key}{suffix}"


def _document(
    reader: Callable[[str], bytes], name: str, seen: frozenset[str]
) -> dict[str, JsonValue]:
    if name in seen or len(seen) > 16:
        raise ValueError("cyclic Minecraft model parent")
    fields = as_mapping(json.loads(reader(_resource(name, "models", ".json"))))
    parent = as_string(fields.get("parent"))
    inherited = _document(reader, parent, seen | {name}) if parent else {}
    textures = as_mapping(inherited.get("textures")) | as_mapping(fields.get("textures"))
    display = as_mapping(inherited.get("display")) | as_mapping(fields.get("display"))
    return inherited | fields | {"textures": textures, "display": display}


def _triple(value: JsonValue) -> tuple[float, float, float]:
    numbers = as_list(value)
    if len(numbers) != 3 or any(not isinstance(n, (int, float)) for n in numbers):
        raise ValueError("invalid Minecraft model vector")
    return float(str(numbers[0])), float(str(numbers[1])), float(str(numbers[2]))


def _decode_model(reader: Callable[[str], bytes], block: str) -> BlockModel:
    fields = _document(reader, f"block/{block}", frozenset())
    textures = as_mapping(fields.get("textures"))
    images: dict[str, QImage] = {}

    def image_for(reference: str) -> QImage:
        visited: set[str] = set()
        while reference.startswith("#"):
            if reference in visited:
                raise ValueError("cyclic Minecraft texture reference")
            visited.add(reference)
            reference = as_string(textures.get(reference[1:])) or ""
        if reference not in images:
            image = QImage()
            # Minecraft textures are PNG; avoid probing Qt's SVG plugin in worker threads.
            texture_data = reader(_resource(reference, "textures", ".png"))
            # PySide 6.11 stubs say bytes, but the binding accepts only str for format.
            if not image.loadFromData(texture_data, "PNG"):  # type: ignore[arg-type]
                raise ValueError("invalid Minecraft texture")
            images[reference] = image.copy(0, 0, image.width(), image.width())
        return images[reference]

    surfaces: list[BlockSurface] = []
    tint = load_biome_tint(reader, block) if block in ("grass_block", "oak_leaves") else None
    for raw_element in as_list(fields.get("elements")):
        element = as_mapping(raw_element)
        low, high = _triple(element.get("from")), _triple(element.get("to"))
        minimum = (low[0] / 8 - 1, 1 - high[1] / 8, low[2] / 8 - 1)
        maximum = (high[0] / 8 - 1, 1 - low[1] / 8, high[2] / 8 - 1)
        for direction, raw_face in as_mapping(element.get("faces")).items():
            face = as_mapping(raw_face)
            name = FACE_NAMES[direction]
            image = image_for(as_string(face.get("texture")) or "")
            uv = as_list(face.get("uv")) or [0, 0, 16, 16]
            u0, v0, u1, v1 = (float(str(n)) * image.width() / 16 for n in uv)
            texture = image.copy(round(u0), round(v0), round(u1 - u0), round(v1 - v0))
            if face.get("tintindex") is not None and tint is not None:
                texture = tinted(texture, tint)
            rotation = face.get("rotation")
            if isinstance(rotation, (int, float)):
                texture = texture.transformed(QTransform().rotate(rotation))
            vertices = tuple(
                (
                    minimum[0] + (x + 1) * (maximum[0] - minimum[0]) / 2,
                    minimum[1] + (y + 1) * (maximum[1] - minimum[1]) / 2,
                    minimum[2] + (z + 1) * (maximum[2] - minimum[2]) / 2,
                )
                for x, y, z in CUBE_FACES[name]
            )
            transparent = image.hasAlphaChannel() and any(
                image.pixelColor(x, y).alpha() < 255
                for y in range(image.height())
                for x in range(image.width())
            )
            if transparent:
                surfaces.append(BlockSurface(name, vertices, texture, layer=0, back_faces=True))
            surfaces.append(BlockSurface(name, vertices, texture, layer=2 if transparent else 1))
    gui = as_mapping(as_mapping(fields.get("display")).get("gui"))
    return BlockModel(tuple(surfaces), _triple(gui.get("rotation")), _triple(gui.get("scale")))


def load_block_model(block: str, jar_path: Path | None = None) -> BlockModel:
    """Ưu tiên model/texture từ client đã cài; phần thiếu dùng bản gốc 1.20.1 đóng kèm."""
    assets_dir = Path(__file__).parent / "qml" / "assets" / "minecraft-blocks"
    if jar_path is not None:
        try:
            with zipfile.ZipFile(jar_path) as archive:

                def read_resource(path: str) -> bytes:
                    try:
                        return archive.read(f"assets/minecraft/{path}")
                    except KeyError:
                        return (assets_dir / path).read_bytes()

                return _decode_model(read_resource, block)
        except (OSError, zipfile.BadZipFile, KeyError, ValueError) as error:
            logger.debug("model Minecraft trong jar không có hoặc không hợp lệ: %s", error)
    return _decode_model(lambda path: (assets_dir / path).read_bytes(), block)
