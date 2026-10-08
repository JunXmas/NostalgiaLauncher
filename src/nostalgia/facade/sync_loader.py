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
    artifact_names = {
        "fabric": "fabric-loader",
        "quilt": "quilt-loader",
        "forge": "forge",
        "neoforge": "neoforge",
    }
    for library in libraries:
        if library.coordinate.artifact == artifact_names[loader_kind]:
            return (
                library.coordinate.artifact_version.removeprefix(game_version + "-")
                if loader_kind == "forge"
                else library.coordinate.artifact_version
            )
    raise MultiplayerError("Không tìm thấy phiên bản loader. Hãy cài lại loader trước khi chia sẻ.")
