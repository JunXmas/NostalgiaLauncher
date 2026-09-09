"""Bản phát hành launcher trên GitHub Releases: phân tích, so phiên bản, chọn gói cho máy này.

Toàn bộ là hàm THUẦN (không mạng, không đĩa) trừ `fetch_latest_release`. So phiên bản viết
tay trên stdlib vì kho không có phụ thuộc runtime: `v1.2.10` > `v1.2.9`, `1.3.0-beta.1` <
`1.3.0`. Tên gói phải theo mẫu `nostalgia-<ver>-<os>-<arch>.zip`, và mọi bản phát hành phải
kèm `SHA256SUMS` — thiếu là từ chối cài, không phải "tạm tin".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from nostalgia.errors import NetworkError
from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints

SUMS_ASSET_NAME = "SHA256SUMS"
BUNDLE_OS_NAMES = {"linux": "linux", "windows": "windows", "macos": "macos", "osx": "macos"}
_VERSION_PATTERN = re.compile(r"^v?(\d+(?:\.\d+)*)(?:[-.]?([0-9A-Za-z.]+))?$")


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    url: str
    size: int


@dataclass(frozen=True, slots=True)
class LauncherRelease:
    """Một bản phát hành: phiên bản (không có chữ v), ghi chú, trang release, các gói đính kèm."""

    launcher_version: str
    notes: str
    page_url: str
    release_assets: tuple[ReleaseAsset, ...]
    prerelease: bool = False

    def asset_named(self, name: str) -> ReleaseAsset | None:
        return next(
            (release_asset for release_asset in self.release_assets if release_asset.name == name),
            None,
        )


def parse_version(text: str) -> tuple[tuple[int, ...], tuple[str, ...]] | None:
    """`v1.2.3-beta.1` → ((1, 2, 3), ("beta", "1")). Không đọc được thì None."""
    match = _VERSION_PATTERN.match(text.strip())
    if match is None:
        return None
    numbers = tuple(int(part) for part in match.group(1).split("."))
    suffix = tuple(part for part in (match.group(2) or "").split(".") if part)
    return numbers, suffix


def is_newer(candidate: str, current: str) -> bool:
    """Bản `candidate` mới hơn `current`? Bản có hậu tố tiền phát hành xếp DƯỚI bản chính
    cùng số; không đọc được phiên bản nào thì coi là không mới (không bao giờ tự cài mù)."""
    parsed_candidate, parsed_current = parse_version(candidate), parse_version(current)
    if parsed_candidate is None or parsed_current is None:
        return False
    numbers_a, suffix_a = parsed_candidate
    numbers_b, suffix_b = parsed_current
    width = max(len(numbers_a), len(numbers_b))
    padded_a = numbers_a + (0,) * (width - len(numbers_a))
    padded_b = numbers_b + (0,) * (width - len(numbers_b))
    if padded_a != padded_b:
        return padded_a > padded_b
    if bool(suffix_a) != bool(suffix_b):
        return not suffix_a  # bản chính mới hơn bản beta cùng số
    return suffix_a > suffix_b


def parse_release(document: JsonValue) -> LauncherRelease | None:
    """Từ JSON của GitHub `releases/latest`. Bản draft hoặc không có tag thì None."""
    fields = as_mapping(document)
    tag = as_string(fields.get("tag_name")) or ""
    if not tag or fields.get("draft") is True:
        return None
    release_assets = tuple(
        ReleaseAsset(
            name=as_string(as_mapping(raw).get("name")) or "",
            url=as_string(as_mapping(raw).get("browser_download_url")) or "",
            size=_size_of(as_mapping(raw).get("size")),
        )
        for raw in as_list(fields.get("assets"))
    )
    return LauncherRelease(
        launcher_version=tag.removeprefix("v"),
        notes=as_string(fields.get("body")) or "",
        page_url=as_string(fields.get("html_url")) or "",
        release_assets=tuple(
            release_asset
            for release_asset in release_assets
            if release_asset.name and release_asset.url
        ),
        prerelease=fields.get("prerelease") is True,
    )


def bundle_asset_name(launcher_version: str, os_name: str, os_arch: str) -> str:
    return f"nostalgia-{launcher_version}-{BUNDLE_OS_NAMES.get(os_name, os_name)}-{os_arch}.zip"


def choose_bundle(release: LauncherRelease, os_name: str, os_arch: str) -> ReleaseAsset | None:
    """Gói đúng hệ điều hành + kiến trúc; không có thì None (bản này không hỗ trợ máy này)."""
    return release.asset_named(bundle_asset_name(release.launcher_version, os_name, os_arch))


def parse_sha256sums(text: str) -> dict[str, str]:
    """Định dạng của `sha256sum`: `<hex>  <tên file>` mỗi dòng; chấp nhận dấu `*` kiểu nhị phân."""
    sums: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            sums[parts[1].lstrip("*").strip()] = parts[0].lower()
    return sums


def fetch_latest_release(
    http_client: HttpClient, *, endpoints: Endpoints = DEFAULT_ENDPOINTS
) -> LauncherRelease | None:
    """CHẠM MẠNG. Chưa có bản phát hành nào (404) thì None, không phải lỗi.

    Đọc MÃ trạng thái thật, không tìm chuỗi "404" trong câu lỗi: câu lỗi chứa cả URL, và một
    cổng hay đường dẫn có "404" trong đó sẽ biến lỗi 500 thành "chưa có bản nào" (đã dính)."""
    url = endpoints.launcher_releases
    response = http_client.send("GET", url, headers={"Accept": "application/vnd.github+json"})
    if response.status == 404:
        return None
    if not response.is_ok:
        raise NetworkError(f"bản phát hành launcher trả {response.status} cho {url}")
    return parse_release(decode_json(response.body, what="bản phát hành launcher"))


def _size_of(value: JsonValue) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0
