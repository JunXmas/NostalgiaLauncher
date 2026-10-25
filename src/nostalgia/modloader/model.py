"""Hình dạng chung của một bản mod loader, bất kể Fabric, Forge hay NeoForge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LoaderKind = Literal["vanilla", "fabric", "quilt", "legacy_fabric", "forge", "neoforge"]
LOADER_KINDS: tuple[LoaderKind, ...] = (
    "vanilla",
    "fabric",
    "quilt",
    "legacy_fabric",
    "forge",
    "neoforge",
)

# Quilt chạy được mod Fabric; khi tìm mod cho bản Quilt thì nhận cả hai. Legacy Fabric tương
# tự: hầu hết mod Fabric cho bản ≤ 1.13.2 chỉ gắn thẻ "fabric" (Modrinth thêm thẻ riêng
# "legacy_fabric" sau này, không phải mod cũ nào cũng có).
COMPATIBLE_LOADERS: dict[LoaderKind, tuple[str, ...]] = {
    "vanilla": (),
    "fabric": ("fabric",),
    "quilt": ("quilt", "fabric"),
    "legacy_fabric": ("legacy_fabric", "fabric"),
    "forge": ("forge",),
    "neoforge": ("neoforge",),
}

# Mã mod mà loader tự khai trong `fabric.mod.json`/`quilt.mod.json` — mod khai phụ thuộc vào
# đúng mã này. Legacy Fabric chạy chính `net.fabricmc:fabric-loader`, nên cùng mã với Fabric.
LOADER_MOD_IDS: dict[str, str] = {
    "fabric": "fabricloader",
    "legacy_fabric": "fabricloader",
    "quilt": "quilt_loader",
}


def loader_mod_id(loader_kind: str) -> str:
    return LOADER_MOD_IDS.get(loader_kind, loader_kind)


# Minecraft 1.14.0 là bản Fabric Loader chính thức đầu tiên hỗ trợ; Legacy Fabric chỉ phủ
# những bản TRƯỚC đó. Hai vùng không chồng nhau nên so sánh đơn giản là đủ, không cần một bộ
# so sánh semver đầy đủ.
_FIRST_MODERN_FABRIC_RELEASE = (1, 14)
# Snapshot dẫn tới 1.14 bắt đầu từ "18w43a" (tháng 10/2018, năm TRƯỚC năm phát hành 2019) —
# cắt ở năm snapshot, không phải năm phát hành.
_FIRST_MODERN_FABRIC_SNAPSHOT_YEAR = 18


def _is_legacy_fabric_game_version(game_version: str) -> bool:
    """`game_version` là phần đuôi của id, ví dụ "1.12.2" hoặc bản snapshot "15w14a".

    Bản phát hành `a.b[.c…]` thì so số; bản snapshot `YYwWWx` thì so hai số đầu của năm —
    Legacy Fabric dừng ở snapshot 2019 (trước 1.14), Fabric hiện đại không lùi về trước đó.
    Nhãn không khớp cả hai dạng (alpha/beta/indev kiểu "b1.7.3") chỉ tồn tại ở Legacy Fabric,
    vì Fabric hiện đại chưa từng và sẽ không bao giờ nhắm tới các bản đó.
    """
    parts = game_version.split(".")
    if parts and parts[0].isdigit():
        release = tuple(int(p) for p in parts[:2] if p.isdigit())
        if len(release) == 2:
            return release < _FIRST_MODERN_FABRIC_RELEASE
    if len(game_version) >= 2 and game_version[:2].isdigit() and "w" in game_version[:5]:
        year = int(game_version[:2])
        return year < _FIRST_MODERN_FABRIC_SNAPSHOT_YEAR
    return True


def detect_loader_kind(version_id: str) -> LoaderKind:
    """Suy loader từ mã bản trong kho — quy ước tên của chính từng loader.

    Thứ tự quan trọng: `neoforge-21.1.9` chứa "forge", nên NeoForge phải xét trước Forge.
    """
    lowered = version_id.lower()
    if lowered.startswith("fabric-loader-"):
        # "fabric-loader-<loader>-<game_version>": tách từ bên phải lấy phần bản game.
        # ponytail: bản game có dấu "-" trong chính tên nó (ví dụ pre-release "1.14-pre1")
        # làm phần tách ra sai (chỉ còn "pre1") → rơi vào nhánh mặc định legacy_fabric. Fabric
        # hiện đại trên pre-release là trường hợp hiếm và chỉ sai nhãn hiển thị, không hỏng cài
        # đặt hay launch. Nâng cấp khi cần: dò theo tập hậu tố pre-release đã biết trước khi tách.
        suffix = version_id[len("fabric-loader-") :]
        _, _, game_version = suffix.rpartition("-")
        return (
            "legacy_fabric"
            if game_version and _is_legacy_fabric_game_version(game_version)
            else "fabric"
        )
    if lowered.startswith("quilt-loader-"):
        return "quilt"
    if "neoforge" in lowered:
        return "neoforge"
    # `1.20.1-forge-47.4.10` (mới) và `1.7.10-Forge10.13.4.1614-1.7.10` (cũ, viết hoa, không gạch).
    if lowered.startswith("forge") or "-forge" in lowered:
        return "forge"
    return "vanilla"


@dataclass(frozen=True, slots=True)
class LoaderVersion:
    """Một bản loader dùng được với một phiên bản game.

    `stable`: Fabric đánh cờ `stable`; Forge là bản `recommended`; NeoForge là bản không
    mang hậu tố `-beta`. `installer_url` rỗng với Fabric (không cần installer).
    """

    loader_version: str
    stable: bool
    installer_url: str = ""
