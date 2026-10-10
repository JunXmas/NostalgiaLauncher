"""Nhận diện loader từ metadata đã cài, không tin classpath do host khai báo."""

import re

from nostalgia.errors import MultiplayerError
from nostalgia.modloader.model import LoaderKind
from nostalgia.version.meta import ArgumentSpec, Library


def resolve_sync_loader(
    loader_kind: LoaderKind,
    libraries: tuple[Library, ...],
    game_version: str,
    *,
    game_arguments: tuple[ArgumentSpec, ...] = (),
) -> str:
    # Chỉ đọc metadata cục bộ; khách vẫn tải installer chính thức theo phiên bản.
    if loader_kind == "vanilla":
        return ""
    coordinate_names = {
        "fabric": (("net.fabricmc", "fabric-loader"),),
        "quilt": (("org.quiltmc", "quilt-loader"),),
        # Forge mới chỉ khai fmlloader trong version.json; forge universal nằm ngoài
        # danh sách thư viện client. Cả hai tọa độ mang cùng phiên bản Forge.
        "forge": (("net.minecraftforge", "forge"), ("net.minecraftforge", "fmlloader")),
        "neoforge": (("net.neoforged", "neoforge"), ("net.neoforged", "forge")),
    }
    for loader_group, loader_artifact in coordinate_names[loader_kind]:
        for library in libraries:
            coordinate = library.coordinate
            if (coordinate.group, coordinate.artifact) == (loader_group, loader_artifact):
                return (
                    coordinate.artifact_version.removeprefix(game_version + "-")
                    if loader_kind == "forge" or loader_artifact == "forge"
                    else coordinate.artifact_version
                )
    if loader_kind == "neoforge":
        # Installer NeoForge thường không khai neoforge trong libraries; FML có
        # số hiệu riêng, không thể dùng thay cho --fml.neoForgeVersion.
        values = tuple(
            value for argument in game_arguments if not argument.rules for value in argument.values
        )
        candidates = {
            values[position + 1]
            for position, value in enumerate(values[:-1])
            if value == "--fml.neoForgeVersion"
            and re.fullmatch(r"[0-9]+(?:\.[0-9]+){2,3}(?:-beta)?", values[position + 1])
        }
        if len(candidates) == 1:
            return candidates.pop()
    raise MultiplayerError("Không tìm thấy phiên bản loader. Hãy cài lại loader trước khi chia sẻ.")
