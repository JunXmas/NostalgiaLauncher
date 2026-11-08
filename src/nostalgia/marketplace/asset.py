"""Gói hình học có giới hạn, không URL, script hoặc mã thực thi."""

import base64
import math
from typing import cast

from nostalgia.errors import SocialError
from nostalgia.model.cosmetic import CosmeticAsset, CosmeticNode, CosmeticPart
from nostalgia.model.json_value import JsonValue, as_mapping
from nostalgia.net.payload import decode_json


def numbers(value: JsonValue, maximum: int, count: int = 0) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) > maximum or (count and len(value) != count):
        raise SocialError("Invalid cosmetic array")
    result: list[float] = []
    for number in value:
        if (
            type(number) not in (int, float)
            or not math.isfinite(cast(float, number))
            or abs(cast(float, number)) > 10000
        ):
            raise SocialError("Invalid cosmetic number")
        result.append(float(cast(float, number)))
    return tuple(result)


def parse_asset(payload: bytes) -> CosmeticAsset:
    if len(payload) > 1_000_000:
        raise SocialError("Cosmetic package exceeds limit")
    fields = as_mapping(decode_json(payload, what="cosmetic asset"))
    raw_parts, encoded = fields.get("parts"), fields.get("texture_png")
    if (
        set(fields) != {"schema_version", "parts", "texture_png"}
        or fields["schema_version"] != 1
        or not isinstance(raw_parts, list)
        or not 1 <= len(raw_parts) <= 6
        or not isinstance(encoded, str)
        or len(encoded) > 350000
    ):
        raise SocialError("Unsupported cosmetic asset")
    try:
        texture = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise SocialError("Invalid cosmetic texture") from error
    if not texture.startswith(b"\x89PNG\r\n\x1a\n") or len(texture) < 57:
        raise SocialError("Invalid cosmetic PNG")
    parts: list[CosmeticPart] = []
    vertex_total = 0
    for raw_part in raw_parts:
        part = as_mapping(raw_part)
        bone, mesh = part.get("bone"), as_mapping(part.get("model"))
        if (
            set(part) != {"bone", "model"}
            or bone not in ("head", "body", "left_arm", "right_arm", "left_leg", "right_leg")
            or any(p.bone == bone for p in parts)
        ):
            raise SocialError("Invalid cosmetic attachment")
        duration, raw_nodes = mesh.get("duration"), mesh.get("nodes")
        if (
            set(mesh) != {"format", "texture", "fps", "duration", "nodes"}
            or mesh.get("format") != 1
            or mesh.get("texture") != "nosclient:cosmetic"
            or mesh.get("fps") != 60
            or type(duration) not in (int, float)
            or not 0 < cast(float, duration) <= 10
            or not isinstance(raw_nodes, list)
            or not 1 <= len(raw_nodes) <= 64
        ):
            raise SocialError("Invalid cosmetic mesh")
        nodes: list[CosmeticNode] = []
        for raw_node in raw_nodes:
            node = as_mapping(raw_node)
            parent_index = node.get("parent")
            if (
                set(node) - {"parent", "translation", "rotation", "vertices", "keys"}
                or type(parent_index) is not int
                or not -1 <= parent_index < len(nodes)
            ):
                raise SocialError("Invalid cosmetic hierarchy")
            translation = numbers(node.get("translation"), 3, 3)
            rotation = numbers(node.get("rotation"), 4, 4)
            vertices = numbers(node.get("vertices"), 32768)
            keys = numbers(node.get("keys", []), 2404)
            if (
                len(vertices) % 32
                or abs(math.hypot(*rotation) - 1) > 0.01
                or (keys and len(keys) != (round(cast(float, duration) * 60) + 1) * 4)
            ):
                raise SocialError("Invalid cosmetic rig")
            if (
                any(abs(n) > 4 for n in translation)
                or any(
                    abs(vertices[p + k]) > 4 for p in range(0, len(vertices), 8) for k in range(3)
                )
                or any(
                    not 0 <= vertices[p + k] <= 1
                    for p in range(0, len(vertices), 8)
                    for k in (3, 4)
                )
            ):
                raise SocialError("Cosmetic geometry exceeds limits")
            vertex_total += len(vertices) // 8
            nodes.append(CosmeticNode(parent_index, translation, rotation, vertices, keys))
        parts.append(CosmeticPart(bone, float(cast(float, duration)), tuple(nodes)))
    if vertex_total > 4096:
        raise SocialError("Cosmetic vertex budget exceeded")
    return CosmeticAsset(texture, tuple(parts))
