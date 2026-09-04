"""Đọc hai tầng manifest của Mojang cho bản Java. THUẦN: chỉ phân tích.

Tầng một (`all.json`) là danh mục: khoá hệ điều hành → component → các bản phát hành.
Tầng hai là manifest của một bản: bảng đường-dẫn → mục, với ba loại `file`, `directory`,
`link`. Đo trên bản thật `jre-legacy/linux`: 391 mục gồm 300 file, 88 thư mục và 3 link.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mccore.model.download import RemoteFile
from mccore.model.json_value import JsonValue, as_list, as_mapping, as_string

FILE = "file"
DIRECTORY = "directory"
LINK = "link"


@dataclass(frozen=True, slots=True)
class RuntimeRelease:
    """Một bản phát hành của một component: trỏ tới manifest chi tiết của nó."""

    java_component: str
    runtime_os_key: str
    version_name: str
    manifest: RemoteFile


@dataclass(frozen=True, slots=True)
class RuntimeCatalog:
    """Danh mục `all.json`, tra theo (khoá hệ điều hành, component)."""

    releases: Mapping[tuple[str, str], RuntimeRelease] = field(default_factory=dict)

    def find(self, java_component: str, runtime_os_keys: tuple[str, ...]) -> RuntimeRelease | None:
        """Thử khoá ưu tiên trước, rồi tới các đường lùi.

        Trả `None` khi không khoá nào có component đó — nghĩa là Mojang không phát hành bản
        Java này cho nền tảng đó, và người gọi phải nói rõ điều đó thay vì hỏng mơ hồ.
        """
        for runtime_os_key in runtime_os_keys:
            release = self.releases.get((runtime_os_key, java_component))
            if release is not None:
                return release
        return None


@dataclass(frozen=True, slots=True)
class RuntimeFile:
    """Một mục trong bản Java.

    `compressed` là bản nén lzma mà Mojang cung cấp cho phần lớn file — đo được nó giảm
    68-77% dung lượng tải. `raw` luôn có, và sha1 của `raw` là thứ phải khớp sau khi bung.
    """

    relative_path: str
    raw: RemoteFile
    compressed: RemoteFile | None = None
    is_executable: bool = False


@dataclass(frozen=True, slots=True)
class RuntimeLayout:
    """Bản Java đã phân tích: thư mục phải tạo, file phải tải, liên kết phải dựng."""

    directories: tuple[str, ...]
    files: tuple[RuntimeFile, ...]
    links: Mapping[str, str] = field(default_factory=dict)


def parse_runtime_catalog(document: JsonValue) -> RuntimeCatalog:
    """Phân tích `all.json`.

    Hai hình dạng thật phải chịu được: một component có thể được **khai mà chưa phát hành
    bản nào** (danh sách rỗng — `mac-os-arm64` với `jre-legacy`), và một component có thể
    có nhiều bản. Lấy bản đầu tiên, đúng như trình khởi động chính thức làm.
    """
    releases: dict[tuple[str, str], RuntimeRelease] = {}
    for runtime_os_key, components in as_mapping(document).items():
        for java_component, entries in as_mapping(components).items():
            first = next(iter(as_list(entries)), None)
            manifest = _parse_remote_file(as_mapping(as_mapping(first).get("manifest")))
            if manifest is None:
                continue
            version_fields = as_mapping(as_mapping(first).get("version"))
            releases[runtime_os_key, java_component] = RuntimeRelease(
                java_component=java_component,
                runtime_os_key=runtime_os_key,
                version_name=as_string(version_fields.get("name")) or "",
                manifest=manifest,
            )
    return RuntimeCatalog(releases=releases)


def parse_runtime_layout(document: JsonValue) -> RuntimeLayout:
    """Phân tích manifest của một bản. Mục sai cấu trúc bị bỏ qua, không làm nổ cả bản."""
    directories: list[str] = []
    files: list[RuntimeFile] = []
    links: dict[str, str] = {}

    for relative_path, raw_entry in as_mapping(as_mapping(document).get("files")).items():
        entry_fields = as_mapping(raw_entry)
        entry_kind = as_string(entry_fields.get("type"))
        if entry_kind == DIRECTORY:
            directories.append(relative_path)
        elif entry_kind == LINK:
            target = as_string(entry_fields.get("target"))
            if target is not None:
                links[relative_path] = target
        elif entry_kind == FILE:
            downloads = as_mapping(entry_fields.get("downloads"))
            raw = _parse_remote_file(as_mapping(downloads.get("raw")))
            if raw is None:
                continue
            files.append(
                RuntimeFile(
                    relative_path=relative_path,
                    raw=raw,
                    compressed=_parse_remote_file(as_mapping(downloads.get("lzma"))),
                    is_executable=entry_fields.get("executable") is True,
                )
            )

    return RuntimeLayout(directories=tuple(directories), files=tuple(files), links=links)


def _parse_remote_file(fields: Mapping[str, JsonValue]) -> RemoteFile | None:
    url = as_string(fields.get("url"))
    if url is None:
        return None
    size = fields.get("size")
    return RemoteFile(
        url=url,
        sha1=as_string(fields.get("sha1")),
        size=size if isinstance(size, int) and not isinstance(size, bool) else None,
    )
