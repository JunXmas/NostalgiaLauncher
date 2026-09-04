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

from mccore.system.platform_info import Platform, classpath_separator
from mccore.version.meta import Library, VersionMeta
from mccore.version.rules import rules_allow


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
    version_meta: VersionMeta,
    platform: Platform,
    libraries_dir: Path,
    client_jar: Path,
) -> tuple[Path, ...]:
    """Đường dẫn đầy đủ, thư viện trước rồi client.jar cuối.

    client.jar đứng cuối vì loader cần các lớp của mình được tìm thấy trước lớp của vanilla.
    """
    paths = [
        libraries_dir / library.coordinate.relative_path
        for library in resolve_classpath_libraries(version_meta, platform)
    ]
    paths.append(client_jar)
    return tuple(paths)


def join_classpath(classpath: tuple[Path, ...], os_name: str) -> str:
    """Nối thành chuỗi cho `-cp`. Dấu ngăn là `;` trên Windows, `:` ở nơi khác."""
    return classpath_separator(os_name).join(str(path) for path in classpath)
