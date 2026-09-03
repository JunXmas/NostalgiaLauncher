"""Trộn `inheritsFrom`: bản của Fabric/Forge chỉ khai vài khoá và dựa vào bản gốc.

Vì sao phải cẩn thận với thứ tự thư viện: Fabric mang theo `asm 9.10.1` trong khi vanilla
khai `asm 9.6`. Nếu để vanilla lên trước, classpath sẽ nạp bản cũ và game chết vì
"duplicate classes found". Thư viện của bản CON luôn đứng trước.

Ngược lại với tham số: bản gốc dựng cả dòng lệnh, bản con chỉ THÊM vào, nên tham số của bản
CHA đứng trước.

Hàm ở đây không đọc file: người gọi truyền vào một hàm nạp JSON thô. Nhờ vậy `version/` vẫn
thuần và test được offline.
"""

from __future__ import annotations

from collections.abc import Callable

from mccore.errors import VersionError
from mccore.model.json_value import JsonValue, as_list, as_mapping, as_string

# Trần độ sâu kế thừa. Thực tế không quá 2 (vanilla <- loader), nhưng một file JSON sửa tay
# có thể tạo chuỗi dài hoặc vòng tròn, và vòng tròn thì phải hỏng RÕ RÀNG chứ không treo.
MAX_INHERITANCE_DEPTH = 8

# Hai nhóm khoá là danh sách và phải NỐI chứ không ghi đè, và thứ tự nối NGƯỢC nhau — xem
# docstring của `merge_inherited`.
PARENT_FIRST_ARGUMENT_GROUPS = ("game", "jvm")

LoadRawVersion = Callable[[str], JsonValue]


def resolve_inheritance(
    version_id: str,
    load_raw_version: LoadRawVersion,
    *,
    max_depth: int = MAX_INHERITANCE_DEPTH,
) -> dict[str, JsonValue]:
    """Nạp một phiên bản và trộn hết chuỗi kế thừa của nó thành một JSON duy nhất.

    `load_raw_version` nhận `version_id` và trả về JSON thô — người gọi lo việc đọc đĩa hay
    tải mạng. Kết quả không còn khoá `inheritsFrom`: nó đã được giải quyết xong.

    Ném `VersionError` khi gặp vòng tròn hoặc chuỗi quá sâu, thay vì lặp vô tận.
    """
    chain: list[dict[str, JsonValue]] = []
    seen: list[str] = []
    current_id: str | None = version_id

    while current_id is not None:
        if current_id in seen:
            trail = " -> ".join([*seen, current_id])
            message = f"kế thừa vòng tròn: {trail}"
            raise VersionError(message)
        if len(chain) >= max_depth:
            message = f"chuỗi kế thừa sâu quá {max_depth} bậc, bắt đầu từ {version_id!r}"
            raise VersionError(message)
        seen.append(current_id)
        current = as_mapping(load_raw_version(current_id))
        if not current:
            message = f"không có dữ liệu cho phiên bản {current_id!r}"
            raise VersionError(message)
        chain.append(current)
        current_id = as_string(current.get("inheritsFrom"))

    merged = chain[-1]
    for child in reversed(chain[:-1]):
        merged = merge_inherited(child, merged)
    merged.pop("inheritsFrom", None)
    return merged


def merge_inherited(
    child: dict[str, JsonValue], parent: dict[str, JsonValue]
) -> dict[str, JsonValue]:
    """Trộn một bản con lên bản cha. Không sửa đối số nào.

    - Khoá thường: bản con ghi đè.
    - `libraries`: con trước, cha sau (loader phải thắng trên classpath).
    - `arguments.game` / `arguments.jvm`: cha trước, con sau (con chỉ thêm vào).
    - `jar`: nếu con không khai thì lấy `jar` của cha, không có nữa thì lấy `id` của cha —
      vì bản con (Fabric) không có jar riêng.
    """
    merged: dict[str, JsonValue] = dict(parent)
    merged.update({key: value for key, value in child.items() if key != "arguments"})

    if "libraries" in child or "libraries" in parent:
        merged["libraries"] = [*as_list(child.get("libraries")), *as_list(parent.get("libraries"))]

    child_arguments = as_mapping(child.get("arguments"))
    parent_arguments = as_mapping(parent.get("arguments"))
    if child_arguments or parent_arguments:
        merged["arguments"] = {
            group: [*as_list(parent_arguments.get(group)), *as_list(child_arguments.get(group))]
            for group in PARENT_FIRST_ARGUMENT_GROUPS
            if group in parent_arguments or group in child_arguments
        }

    inherited_jar = as_string(child.get("jar")) or as_string(parent.get("jar"))
    jar_owner = inherited_jar or as_string(parent.get("id"))
    if jar_owner is not None:
        merged["jar"] = jar_owner
    return merged
