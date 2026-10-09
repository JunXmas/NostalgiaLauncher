"""Nhận diện loader đã cài từ tọa độ thư viện, không tin classpath do host khai báo."""

from nostalgia.errors import MultiplayerError
from nostalgia.modloader.model import LoaderKind
from nostalgia.version.meta import Library


def resolve_sync_loader(
    loader_kind: LoaderKind, libraries: tuple[Library, ...], game_version: str
) -> str:
    # Chỉ nhận phiên bản từ tọa độ loader đã cài; không chuyển JSON/classpath của host sang khách.
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
    raise MultiplayerError("Không tìm thấy phiên bản loader. Hãy cài lại loader trước khi chia sẻ.")
