"""Danh mục phiên bản của Mojang: 909 bản, 268 KB.

Tra theo mã phiên bản là thao tác lặp lại (mỗi bản trong chuỗi kế thừa một lần), nên danh
mục giữ sẵn một bảng tra thay vì quét tuyến tính. Với 909 mục thì quét cũng không chậm,
nhưng bảng tra khiến chi phí không phụ thuộc số phiên bản — và Mojang chỉ thêm chứ không bớt.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from mccore.errors import DataFileError
from mccore.model.download import RemoteFile
from mccore.model.json_value import JsonValue, as_list, as_mapping, as_string
from mccore.net.http import HttpClient
from mccore.repo.endpoints import VERSION_MANIFEST_URL

RELEASE = "release"
SNAPSHOT = "snapshot"


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """Một dòng trong danh mục: đủ để tải file JSON của phiên bản và xác minh nó."""

    version_id: str
    release_type: str
    remote: RemoteFile
    release_time: str | None = None


@dataclass(frozen=True, slots=True)
class VersionManifest:
    """Danh mục đã phân tích. `entries_by_id` giữ nguyên thứ tự máy chủ: mới nhất trước."""

    entries_by_id: Mapping[str, ManifestEntry]
    latest_release_id: str | None = None
    latest_snapshot_id: str | None = None

    def find(self, version_id: str) -> ManifestEntry | None:
        return self.entries_by_id.get(version_id)

    def released(self) -> tuple[ManifestEntry, ...]:
        """Chỉ bản chính thức, bỏ snapshot và các bản thử nghiệm cũ."""
        return tuple(
            manifest_entry
            for manifest_entry in self.entries_by_id.values()
            if manifest_entry.release_type == RELEASE
        )


def parse_manifest(document: JsonValue) -> VersionManifest:
    """Phân tích danh mục. Mục thiếu `id` hoặc `url` bị bỏ qua thay vì làm hỏng cả danh mục."""
    document_fields = as_mapping(document)
    latest = as_mapping(document_fields.get("latest"))
    entries: dict[str, ManifestEntry] = {}
    for raw_entry in as_list(document_fields.get("versions")):
        fields = as_mapping(raw_entry)
        version_id = as_string(fields.get("id"))
        url = as_string(fields.get("url"))
        if version_id is None or url is None or version_id in entries:
            continue
        entries[version_id] = ManifestEntry(
            version_id=version_id,
            release_type=as_string(fields.get("type")) or "",
            remote=RemoteFile(url=url, sha1=as_string(fields.get("sha1"))),
            release_time=as_string(fields.get("releaseTime")),
        )
    return VersionManifest(
        entries_by_id=entries,
        latest_release_id=as_string(latest.get("release")),
        latest_snapshot_id=as_string(latest.get("snapshot")),
    )


def fetch_manifest(http_client: HttpClient, *, url: str = VERSION_MANIFEST_URL) -> VersionManifest:
    """Tải danh mục từ Mojang. Chạm mạng — tên hàm nói đúng điều đó.

    `url` là tham số để test trỏ sang máy chủ cục bộ. Không có nó, test buộc phải sửa hằng
    ở mức module, và giá trị đã sửa còn nguyên cho mọi test chạy sau — đúng loại trạng thái
    dùng chung mà kho này cấm.
    """
    payload = http_client.fetch_bytes(url)
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        message = f"danh mục phiên bản không phải JSON hợp lệ: {exc}"
        raise DataFileError(message) from exc
    manifest = parse_manifest(document)
    if not manifest.entries_by_id:
        message = "danh mục phiên bản rỗng — máy chủ trả về thứ không dùng được"
        raise DataFileError(message)
    return manifest
