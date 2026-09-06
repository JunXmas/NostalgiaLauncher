"""Hình dạng duy nhất của nội dung cài thêm, bất kể nguồn."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nostalgia.modloader.model import COMPATIBLE_LOADERS, LoaderKind

ContentKind = Literal["mod", "resourcepack", "shader", "modpack"]
CONTENT_KINDS: tuple[ContentKind, ...] = ("mod", "resourcepack", "shader", "modpack")

# Nguồn nội dung. CurseForge cần khoá API của chính người dùng (xem settings/).
ContentSource = Literal["modrinth", "curseforge"]

# Thư mục đích trong thư mục bản chơi, theo quy ước của chính game và của Iris/OptiFine.
# Modpack không có thư mục: nó thành một bản chơi mới (xem content/mrpack.py).
FOLDER_BY_KIND: dict[ContentKind, str] = {
    "mod": "mods",
    "resourcepack": "resourcepacks",
    "shader": "shaderpacks",
}

# Loader của bản chơi lấy từ modloader/model.py. "vanilla" nghĩa là không loader: không cài
# mod được, nhưng gói tài nguyên và shader thì vẫn cài được.

SortOrder = Literal["relevance", "downloads", "follows", "newest", "updated"]


@dataclass(frozen=True, slots=True)
class Project:
    """Một dự án trên nguồn nội dung: một mod, một gói tài nguyên, một shader."""

    project_id: str
    project_slug: str
    title: str
    description: str
    author: str
    content_kind: ContentKind
    icon_url: str
    downloads: int
    follows: int
    loaders: tuple[str, ...]
    source: ContentSource = "modrinth"


@dataclass(frozen=True, slots=True)
class SearchPage:
    """Một trang kết quả tìm kiếm; `total_hits` để biết còn trang sau hay không."""

    hits: tuple[Project, ...]
    offset: int
    total_hits: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.hits) < self.total_hits


@dataclass(frozen=True, slots=True)
class ProjectVersion:
    """Một bản phát hành của dự án, kèm file chính để tải."""

    version_id: str
    project_id: str
    version_number: str
    version_type: str  # release | beta | alpha
    game_versions: tuple[str, ...]
    loaders: tuple[str, ...]
    date_published: str
    file_url: str
    file_name: str
    file_sha1: str
    file_size: int
    required_project_ids: tuple[str, ...]

    def supports(
        self, game_version: str, loader_kind: LoaderKind, content_kind: ContentKind
    ) -> bool:
        """Mod phải khớp cả phiên bản game lẫn loader; gói tài nguyên và shader chỉ cần
        phiên bản game — loader của chúng (iris, optifine, minecraft) không liên quan."""
        if game_version not in self.game_versions:
            return False
        if content_kind not in ("mod", "modpack"):
            return True
        return any(name in self.loaders for name in COMPATIBLE_LOADERS[loader_kind])


@dataclass(frozen=True, slots=True)
class InstalledContent:
    """Một file đang nằm trong thư mục bản chơi, kèm nguồn gốc nếu biết."""

    content_kind: ContentKind
    file_name: str
    file_size: int
    enabled: bool
    project_id: str = ""
    title: str = ""
    version_id: str = ""
    version_number: str = ""
    icon_url: str = ""

    @property
    def label(self) -> str:
        return self.title or self.file_name


__all__ = ["LoaderKind"]
