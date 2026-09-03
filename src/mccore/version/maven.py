"""Toạ độ maven `group:artifact:version[:classifier]` và đường dẫn nó tương ứng.

Mojang khai thư viện bằng toạ độ này, và đường dẫn trong kho `libraries/` suy ra từ nó theo
một quy tắc duy nhất. Viết ở đúng một chỗ để không ai nối tay ở chỗ thứ hai rồi lệch.
"""

from __future__ import annotations

from dataclasses import dataclass

JAR_EXTENSION = "jar"


@dataclass(frozen=True, slots=True)
class MavenCoordinate:
    """Toạ độ đã phân tích. `classifier` là hậu tố như `natives-linux`."""

    group: str
    artifact: str
    version: str
    classifier: str | None = None

    @classmethod
    def parse(cls, name: str) -> MavenCoordinate:
        """Phân tích `org.lwjgl:lwjgl-glfw:3.3.1:natives-linux`.

        Forge dùng thêm hậu tố kiểu `@zip` để đổi phần mở rộng; vanilla và Fabric thì không,
        nên chưa xử lý — sẽ thêm ở bước làm Forge, kèm test riêng.
        """
        parts = name.split(":")
        if len(parts) < 3:
            message = f"toạ độ maven phải có ít nhất group:artifact:version, nhận {name!r}"
            raise ValueError(message)
        group, artifact, version = parts[0], parts[1], parts[2]
        classifier = parts[3] if len(parts) > 3 and parts[3] else None
        return cls(group=group, artifact=artifact, version=version, classifier=classifier)

    @property
    def relative_path(self) -> str:
        """Đường dẫn tương đối trong `libraries/`, dùng `/` kể cả trên Windows.

        Đây là chuỗi cho URL và cho khoá trong JSON, nên luôn là `/`; việc đổi sang đường
        dẫn của hệ thống là việc của `resolve_within`.
        """
        suffix = f"-{self.classifier}" if self.classifier else ""
        file_name = f"{self.artifact}-{self.version}{suffix}.{JAR_EXTENSION}"
        return f"{self.group.replace('.', '/')}/{self.artifact}/{self.version}/{file_name}"

    @property
    def dedupe_key(self) -> str:
        """Khoá gộp trùng: **không có version**.

        Fabric mang theo `asm 9.10.1` trong khi vanilla khai `asm 9.6`; để cả hai lên
        classpath là lỗi "duplicate classes found" mà launcher tiền nhiệm từng gặp. Gộp theo
        khoá này rồi giữ bản xuất hiện trước (thứ tự đã đặt loader lên đầu).
        """
        suffix = f":{self.classifier}" if self.classifier else ""
        return f"{self.group}:{self.artifact}{suffix}"

    def __str__(self) -> str:
        suffix = f":{self.classifier}" if self.classifier else ""
        return f"{self.group}:{self.artifact}:{self.version}{suffix}"
