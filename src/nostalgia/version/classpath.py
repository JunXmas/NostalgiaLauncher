"""Dựng classpath cho java. THUẦN: không chạm đĩa, không kiểm file có tồn tại hay không.

Ba luật, cả ba đều là lỗi thật của launcher tiền nhiệm nếu làm sai:

- **Lọc theo `rules`** cho đúng hệ điều hành đang chạy.
- **Bỏ jar natives ra khỏi classpath.** Chúng chỉ chứa `.so`/`.dll`; với kiểu cũ thì mỗi hệ
  điều hành một file khác nhau nên đưa vào còn sai.
- **Gộp trùng theo `group:artifact[:classifier]`, GIỮ BẢN ĐẦU.** Fabric mang `asm 9.10.1`
  còn vanilla khai `asm 9.6`; thứ tự trộn kế thừa đã đặt loader lên trước, nên giữ bản đầu
  là giữ bản của loader. Để cả hai lên classpath là lỗi "duplicate classes found".
"""

from __future__ import annotations

from pathlib import Path

from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform, classpath_separator
from nostalgia.version.meta import Library, VersionMeta
from nostalgia.version.rules import rules_allow


def resolve_classpath_libraries(
    version_meta: VersionMeta, platform: Platform
) -> tuple[Library, ...]:
    """Thư viện nào thật sự lên classpath, theo đúng thứ tự đã khai."""
    chosen: list[Library] = []
    seen: set[str] = set()
    for library in version_meta.libraries:
        if not library.is_classpath_entry:
            continue
        if not rules_allow(library.rules, platform):
            continue
        key = library.coordinate.dedupe_key
        if key in seen:
            continue
        seen.add(key)
        chosen.append(library)
    return tuple(chosen)


def resolve_classpath(
    version_meta: VersionMeta, platform: Platform, paths: DataPaths
) -> tuple[Path, ...]:
    """Đường dẫn đầy đủ, thư viện trước rồi client.jar cuối.

    client.jar đứng cuối vì loader cần các lớp của mình được tìm thấy trước lớp của vanilla.

    Nhận `DataPaths` chứ không nhận sẵn đường dẫn jar: bản trước để người gọi tự truyền, và
    người gọi rất dễ truyền theo `version_id` vì đó là thứ họ đang cầm — trong khi bản của
    loader dùng jar của bản gốc. Đã dựng ca chứng minh: classpath trỏ tới
    `fabric-loader-....jar` còn bộ tải lại tải về `1.21.4.jar`, và không gì trong code chặn.
    Nay chỉ một chỗ biết luật đó.
    """
    entries = [
        paths.libraries_dir / library.coordinate.relative_path
        for library in resolve_classpath_libraries(version_meta, platform)
    ]
    entries.append(paths.version_jar(version_meta.jar_owner_id))
    return tuple(entries)


def join_classpath(classpath: tuple[Path, ...], os_name: str) -> str:
    """Nối thành chuỗi cho `-cp`. Dấu ngăn là `;` trên Windows, `:` ở nơi khác."""
    return classpath_separator(os_name).join(str(path) for path in classpath)
