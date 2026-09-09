"""Âm thanh của launcher, KHÔNG thêm thư viện.

QtMultimedia nằm trong PySide6-Addons (~150 MB) — không đáng chỉ vì vài tiếng bíp. Thay vào
đó: tự tổng hợp WAV bằng stdlib (`synth.py`), ghi ra cache một lần, rồi phát bằng trình phát
có sẵn của hệ điều hành (`paplay`/`aplay`/`pw-play` trên Linux, `afplay` trên macOS,
`winsound` trên Windows) — không chặn, không có gì để phát thì im lặng.

Hai họ tiếng: CHUÔNG vài nốt cho sự kiện game (khởi động / thoát / cài xong) và TIẾNG GIAO
DIỆN dựng theo dashboard Xbox 360 / Steam Big Picture — chuông kính, hơi gió, "thụp" trầm,
vang phòng — cho chuyển trang, bấm nút, bung / thu thẻ. Đặt `NOSTALGIA_SILENT=1` để tắt hẳn
(test, CI): không sinh file, không gọi trình phát.
"""

from __future__ import annotations

import hashlib
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

from nostalgia.ui.synth import SAMPLE_RATE, bell, blip, echo, overlay, soften, to_pcm, whoosh

NOTE_SECONDS = 0.13
VOLUME = 0.35
# Tiếng giao diện nhỏ hơn chuông và không có gì trên ~2,5 kHz: bản đầu (đỉnh 0,3, gió tới
# 7 kHz) bị chê "khó nghe, nhức đầu".
UI_PEAK = 0.2
UI_CUTOFF_HZ = 2500.0
SILENT_ENV = "NOSTALGIA_SILENT"

# Mỗi sự kiện một giai điệu ngắn: lên = tốt, xuống = xong, trầm = hỏng.
CHIMES: dict[str, tuple[float, ...]] = {
    "started": (659.3, 880.0),
    "stopped": (659.3, 440.0),
    "crashed": (330.0, 220.0),
    "installed": (523.3, 659.3, 784.0),
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


def finish(layers: list[float]) -> bytes:
    """Cắt dải cao rồi đóng gói — mọi tiếng giao diện đi qua đây cho cùng một "màu"."""
    return wrap_wav(to_pcm(soften(layers, UI_CUTOFF_HZ), UI_PEAK))


def render_nav() -> bytes:
    """Chuyển ô (thanh bên, loader): blip 8-bit lướt lên 880→1175 Hz, 70 ms — cú thụp trầm
    kiểu Steam Big Picture bị chê khó nghe, jun muốn giữ tiếng 8-bit ở đây."""
    return finish(
        overlay(
            (blip(880.0, 1174.7, 0.07), 1.0, 0.0),
        )
    )


def render_select() -> bytes:
    """Xbox 360 chọn: hai nốt chuông mềm đi lên (C5 → E5) cách 80 ms, vang phòng nhẹ."""
    return finish(
        echo(
            overlay(
                (bell(523.3, 0.30), 0.8, 0.0),
                (bell(659.3, 0.36), 1.0, 0.08),
            ),
            0.09,
            0.15,
        )
    )


def render_open() -> bytes:
    """Mở hộp / bung thẻ: hơi gió trầm thổi lên 0,26 s, giữa chừng điểm một nốt G4 mềm."""
    return finish(
        echo(
            overlay(
                (whoosh(0.26, 250.0, 1500.0, noise_seed=3, swell=0.55), 0.6, 0.0),
                (bell(392.0, 0.30), 0.7, 0.12),
            ),
            0.08,
            0.12,
        )
    )


def render_back() -> bytes:
    """Lùi / đóng: hơi gió xẹp xuống 0,2 s, kèm nốt E4 trầm ngắn ngay đầu."""
    return finish(
        overlay(
            (whoosh(0.20, 1500.0, 250.0, noise_seed=4, swell=0.25), 0.6, 0.0),
            (bell(329.6, 0.22), 0.6, 0.01),
        )
    )


UI_SOUNDS: dict[str, Callable[[], bytes]] = {
    "nav": render_nav,
    "select": render_select,
    "open": render_open,
    "back": render_back,
}


def render_sound(sound_name: str) -> bytes:
    """Tiếng giao diện nếu có tên trong UI_SOUNDS, còn lại là chuông sự kiện (lạ → 'stopped')."""
    renderer = UI_SOUNDS.get(sound_name)
    if renderer is not None:
        return renderer()
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
        self._rendered: dict[str, Path] = {}

    def sound_path(self, sound_name: str) -> Path:
        """File cache mang băm nội dung: đổi công thức tổng hợp là tên đổi theo, bản cũ cùng
        tên tiếng bị dọn — không bao giờ phát nhầm tiếng của phiên bản trước. Mỗi tiếng chỉ
        dựng một lần mỗi tiến trình."""
        cached = self._rendered.get(sound_name)
        if cached is not None:
            return cached
        rendered = render_sound(sound_name)
        digest = hashlib.sha1(rendered).hexdigest()[:8]
        path = self._cache_dir / f"sound-{sound_name}-{digest}.wav"
        if not path.is_file():
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            for stale in self._cache_dir.glob(f"sound-{sound_name}-*.wav"):
                stale.unlink(missing_ok=True)
            path.write_bytes(rendered)
        self._rendered[sound_name] = path
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
