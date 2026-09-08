"""Tiếng "ting" cho thông báo, KHÔNG thêm thư viện.

QtMultimedia nằm trong PySide6-Addons (~150 MB) — không đáng chỉ vì một tiếng chuông. Thay
vào đó: tự tổng hợp WAV vài nốt bằng `wave`/`math` của stdlib, ghi ra cache một lần, rồi phát
bằng trình phát có sẵn của hệ điều hành (`paplay`/`aplay`/`pw-play` trên Linux, `afplay`
trên macOS, `winsound` trên Windows) — không chặn, không có gì để phát thì im lặng.
"""

from __future__ import annotations

import io
import math
import shutil
import struct
import subprocess
import sys
import wave
from collections.abc import Callable, Sequence
from pathlib import Path

SAMPLE_RATE = 22050
NOTE_SECONDS = 0.13
VOLUME = 0.35

# Mỗi sự kiện một giai điệu ngắn: lên = tốt, xuống = xong, trầm = hỏng.
CHIMES: dict[str, tuple[float, ...]] = {
    "started": (659.3, 880.0),
    "stopped": (659.3, 440.0),
    "crashed": (330.0, 220.0),
    "installed": (523.3, 659.3, 784.0),
}

type SpawnFn = Callable[[Sequence[str]], object]
type WhichFn = Callable[[str], str | None]


def render_chime(frequencies: Sequence[float]) -> bytes:
    """WAV mono 16-bit: mỗi nốt là sóng sin tắt dần, nối tiếp nhau."""
    frames = bytearray()
    note_length = int(SAMPLE_RATE * NOTE_SECONDS)
    for frequency in frequencies:
        for position in range(note_length):
            envelope = min(1.0, (note_length - position) / (note_length * 0.7))
            angle = 2 * math.pi * frequency * position / SAMPLE_RATE
            frames += struct.pack("<h", int(VOLUME * 32767 * envelope * math.sin(angle)))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(SAMPLE_RATE)
        writer.writeframes(bytes(frames))
    return buffer.getvalue()


def resolve_player_command(platform_name: str, which: WhichFn = shutil.which) -> tuple[str, ...]:
    """Lệnh phát một file WAV. Rỗng = máy không có trình phát nào (im lặng, không phải lỗi).
    Windows không cần lệnh: `winsound` của stdlib phát trực tiếp."""
    if platform_name == "darwin":
        return ("afplay",) if which("afplay") else ()
    if platform_name.startswith("linux"):
        for candidate in ("paplay", "aplay", "pw-play"):
            if which(candidate):
                return (candidate,)
    return ()


def spawn_quietly(argv: Sequence[str]) -> object:
    """Chạy trình phát nền, không chờ, không dính stdio của launcher."""
    return subprocess.Popen(
        list(argv),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class SoundPlayer:
    """Phát chuông theo tên sự kiện. File WAV sinh ra ở lần phát đầu và giữ trong cache."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        platform_name: str = sys.platform,
        spawn: SpawnFn = spawn_quietly,
        which: WhichFn = shutil.which,
    ) -> None:
        self._cache_dir = cache_dir
        self._platform_name = platform_name
        self._spawn = spawn
        self._command = resolve_player_command(platform_name, which)

    def chime_path(self, event_kind: str) -> Path:
        path = self._cache_dir / f"chime-{event_kind}.wav"
        if not path.is_file():
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(render_chime(CHIMES.get(event_kind, CHIMES["stopped"])))
        return path

    def play(self, event_kind: str) -> bool:
        """True nếu đã phát (hoặc đã giao cho hệ điều hành phát)."""
        try:
            path = self.chime_path(event_kind)
            if self._platform_name == "win32":
                return play_with_winsound(path)
            if not self._command:
                return False
            self._spawn([*self._command, str(path)])
            return True
        except OSError:
            return False


def play_with_winsound(path: Path) -> bool:
    """Windows: stdlib phát thẳng, không chặn. Ở hệ khác thì không có gì để làm."""
    if sys.platform == "win32":
        import winsound

        flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
        winsound.PlaySound(str(path), flags)
        return True
    return False
