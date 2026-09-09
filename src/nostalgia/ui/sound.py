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

from nostalgia.ui.synth import SAMPLE_RATE, bell, echo, overlay, thump, to_pcm, whoosh

NOTE_SECONDS = 0.13
VOLUME = 0.35
UI_PEAK = 0.3
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


def render_nav() -> bytes:
    """Steam Big Picture chuyển ô: một cái "tụp" — thụp trầm 240→150 Hz cộng hơi gió 50 ms."""
    layers = overlay(
        (thump(240.0, 150.0, 0.06, decay_rate=60.0), 1.0, 0.0),
        (whoosh(0.05, 2500.0, 600.0, noise_seed=1, swell=0.2), 0.35, 0.0),
    )
    return wrap_wav(to_pcm(layers, UI_PEAK))


def render_select() -> bytes:
    """Xbox 360 chọn: hai nốt chuông kính đi lên (E5 → A5) cách 70 ms, chút lấp lánh gió,
    vang phòng ngắn."""
    layers = overlay(
        (bell(659.3, 0.32), 0.8, 0.0),
        (bell(880.0, 0.38), 1.0, 0.07),
        (whoosh(0.12, 1500.0, 7000.0, noise_seed=2, swell=0.3), 0.12, 0.0),
    )
    return wrap_wav(to_pcm(echo(layers, 0.09, 0.22), UI_PEAK))


def render_open() -> bytes:
    """Mở hộp / bung thẻ: gió thổi lên sáng dần 0,28 s, giữa chừng điểm một nốt kính C5."""
    layers = overlay(
        (whoosh(0.28, 350.0, 6000.0, noise_seed=3, swell=0.55), 0.7, 0.0),
        (bell(523.3, 0.3), 0.6, 0.14),
    )
    return wrap_wav(to_pcm(echo(layers, 0.08, 0.18), UI_PEAK))


def render_back() -> bytes:
    """Lùi / đóng: gió xẹp xuống tối dần 0,22 s, kèm nốt kính trầm G4 ngắn ngay đầu."""
    layers = overlay(
        (whoosh(0.22, 5000.0, 300.0, noise_seed=4, swell=0.25), 0.7, 0.0),
        (bell(392.0, 0.22), 0.5, 0.01),
    )
    return wrap_wav(to_pcm(layers, UI_PEAK))


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
