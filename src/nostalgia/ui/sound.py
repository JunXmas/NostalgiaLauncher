"""Âm thanh của launcher, KHÔNG thêm thư viện.

QtMultimedia nằm trong PySide6-Addons (~150 MB) — không đáng chỉ vì vài tiếng bíp. Thay vào
đó: tự tổng hợp WAV bằng `wave`/`math` của stdlib, ghi ra cache một lần, rồi phát bằng trình
phát có sẵn của hệ điều hành (`paplay`/`aplay`/`pw-play` trên Linux, `afplay` trên macOS,
`winsound` trên Windows) — không chặn, không có gì để phát thì im lặng.

Hai họ tiếng: CHUÔNG vài nốt cho sự kiện game (khởi động / thoát / cài xong) và BLIP giao
diện kiểu Xbox 360 dashboard / Steam Big Picture — một nốt sin lướt cao độ, bồi âm nhẹ, phong
bì mềm — cho chuyển trang, bấm nút, bung / thu thẻ. Đặt `NOSTALGIA_SILENT=1` để tắt hẳn
(test, CI): không sinh file, không gọi trình phát.
"""

from __future__ import annotations

import io
import math
import os
import shutil
import struct
import subprocess
import sys
import wave
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

SAMPLE_RATE = 22050
NOTE_SECONDS = 0.13
VOLUME = 0.35
BLIP_VOLUME = 0.22
SILENT_ENV = "NOSTALGIA_SILENT"

# Mỗi sự kiện một giai điệu ngắn: lên = tốt, xuống = xong, trầm = hỏng.
CHIMES: dict[str, tuple[float, ...]] = {
    "started": (659.3, 880.0),
    "stopped": (659.3, 440.0),
    "crashed": (330.0, 220.0),
    "installed": (523.3, 659.3, 784.0),
}
# Blip giao diện: (Hz đầu, Hz cuối, giây). Lướt lên = tiến tới, lướt xuống = lùi lại.
BLIPS: dict[str, tuple[float, float, float]] = {
    "nav": (880.0, 1174.7, 0.07),
    "select": (523.3, 784.0, 0.15),
    "open": (329.6, 659.3, 0.22),
    "back": (659.3, 329.6, 0.18),
}

type SpawnFn = Callable[[Sequence[str]], object]
type WhichFn = Callable[[str], str | None]


def wrap_wav(frames: bytes) -> bytes:
    """Đóng gói mẫu 16-bit mono thành file WAV trong bộ nhớ."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(SAMPLE_RATE)
        writer.writeframes(frames)
    return buffer.getvalue()


def render_chime(frequencies: Sequence[float]) -> bytes:
    """WAV mono 16-bit: mỗi nốt là sóng sin tắt dần, nối tiếp nhau."""
    frames = bytearray()
    note_length = int(SAMPLE_RATE * NOTE_SECONDS)
    for frequency in frequencies:
        for position in range(note_length):
            envelope = min(1.0, (note_length - position) / (note_length * 0.7))
            angle = 2 * math.pi * frequency * position / SAMPLE_RATE
            frames += struct.pack("<h", int(VOLUME * 32767 * envelope * math.sin(angle)))
    return wrap_wav(bytes(frames))


def render_blip(start_hz: float, end_hz: float, seconds: float) -> bytes:
    """Một nốt sin lướt từ `start_hz` tới `end_hz` (theo cấp số nhân — tai nghe đều hơn tuyến
    tính), thêm bồi âm bậc hai nhỏ cho ấm; vào 8 ms, tắt dần theo nửa cosin cho mềm — tiếng
    "bloop" của dashboard, không phải tiếng bíp vuông."""
    frames = bytearray()
    total = int(SAMPLE_RATE * seconds)
    attack = max(1, int(SAMPLE_RATE * 0.008))
    phase = 0.0
    for position in range(total):
        progress = position / total
        frequency = start_hz * (end_hz / start_hz) ** progress
        phase += 2 * math.pi * frequency / SAMPLE_RATE
        envelope = min(1.0, position / attack) * (0.5 + 0.5 * math.cos(math.pi * progress))
        sample = (math.sin(phase) + 0.2 * math.sin(2 * phase)) / 1.2
        frames += struct.pack("<h", int(BLIP_VOLUME * 32767 * envelope * sample))
    return wrap_wav(bytes(frames))


def render_sound(sound_name: str) -> bytes:
    """Blip giao diện nếu có tên trong BLIPS, còn lại là chuông sự kiện (lạ → chuông 'stopped')."""
    if sound_name in BLIPS:
        return render_blip(*BLIPS[sound_name])
    return render_chime(CHIMES.get(sound_name, CHIMES["stopped"]))


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
    """Phát tiếng theo tên. File WAV sinh ra ở lần phát đầu và giữ trong cache."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        platform_name: str = sys.platform,
        spawn: SpawnFn = spawn_quietly,
        which: WhichFn = shutil.which,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        environ = os.environ if environment is None else environment
        self._muted = environ.get(SILENT_ENV, "") == "1"
        self._cache_dir = cache_dir
        self._platform_name = platform_name
        self._spawn = spawn
        self._command = resolve_player_command(platform_name, which)

    def sound_path(self, sound_name: str) -> Path:
        path = self._cache_dir / f"sound-{sound_name}.wav"
        if not path.is_file():
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(render_sound(sound_name))
        return path

    def play(self, sound_name: str) -> bool:
        """True nếu đã phát (hoặc đã giao cho hệ điều hành phát)."""
        if self._muted:
            return False
        try:
            path = self.sound_path(sound_name)
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
