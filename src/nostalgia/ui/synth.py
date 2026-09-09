"""Bộ tổng hợp tí hon (stdlib) cho tiếng giao diện.

Dashboard Xbox 360 / Steam Big Picture nghe "kính và gió" chứ không phải bíp: chuông nhiều bồi
âm tắt dần, hơi gió là ồn trắng qua lọc thông thấp có tần số cắt lướt, một cú "thụp" trầm khi
chuyển ô, và vang phòng ngắn. Ở đây chỉ có đúng bốn viên gạch đó, trả về dãy mẫu float
(-1..1) để `sound.py` chồng lớp và đóng gói WAV. Ồn trắng gieo hạt cố định nên cùng tên tiếng
luôn ra cùng file (cache và test ổn định).
"""

from __future__ import annotations

import math
import random
import struct

SAMPLE_RATE = 22050
# Bồi âm chuông: (bội số tần số, biên độ). Chỉ ba bồi âm, bồi âm cao rất nhỏ — bản năm bồi âm
# lên tới 5,4 lần nghe "chói, nhức đầu" (jun, 09/2026); hơi lệch số nguyên cho chút "thuỷ tinh".
BELL_PARTIALS = ((1.0, 1.0), (2.0, 0.3), (3.01, 0.08))

type Track = list[float]


def frames_for(seconds: float) -> int:
    return max(1, int(SAMPLE_RATE * seconds))


def thump(start_hz: float, end_hz: float, seconds: float, *, decay_rate: float) -> Track:
    """Sin lướt cao độ (cấp số nhân) tắt dần theo hàm mũ — cú "thụp" trầm rất ngắn."""
    total = frames_for(seconds)
    phase = 0.0
    track: Track = []
    for position in range(total):
        progress = position / total
        phase += 2 * math.pi * start_hz * (end_hz / start_hz) ** progress / SAMPLE_RATE
        track.append(math.sin(phase) * math.exp(-decay_rate * position / SAMPLE_RATE))
    return track


def bell(frequency: float, seconds: float) -> Track:
    """Chuông mềm: các bồi âm cùng vào trong 10 ms (vào 3 ms nghe gắt), bồi âm càng cao tắt
    càng nhanh; nốt còn -60 dB đúng lúc hết `seconds`."""
    total = frames_for(seconds)
    attack = frames_for(0.010)
    base_rate = 6.9 / seconds
    track: Track = []
    for position in range(total):
        moment = position / SAMPLE_RATE
        value = 0.0
        for ratio, amplitude in BELL_PARTIALS:
            decay = math.exp(-base_rate * ratio**0.6 * moment)
            value += amplitude * decay * math.sin(2 * math.pi * frequency * ratio * moment)
        track.append(value * min(1.0, position / attack))
    return track


def whoosh(
    seconds: float, start_hz: float, end_hz: float, *, noise_seed: int, swell: float
) -> Track:
    """Gió: ồn trắng qua lọc thông thấp HAI tầng (12 dB/oct — một tầng để lọt quá nhiều xì),
    tần số cắt lướt từ `start_hz` tới `end_hz` (lên = sáng dần, xuống = tối dần); phồng lên
    tới đỉnh ở `swell` phần thời gian rồi xẹp."""
    total = frames_for(seconds)
    rng = random.Random(noise_seed)
    first = second = 0.0
    track: Track = []
    for position in range(total):
        progress = position / total
        cutoff = start_hz * (end_hz / start_hz) ** progress
        alpha = 1 - math.exp(-2 * math.pi * cutoff / SAMPLE_RATE)
        first += alpha * (rng.uniform(-1.0, 1.0) - first)
        second += alpha * (first - second)
        shape = progress / swell if progress < swell else (1 - progress) / (1 - swell)
        track.append(second * math.sin(math.pi / 2 * shape) ** 2)
    return track


def soften(track: Track, cutoff_hz: float) -> Track:
    """Cắt dải cao toàn bộ hỗn hợp (lọc thông thấp hai tầng): dashboard nghe "tròn", không xì."""
    alpha = 1 - math.exp(-2 * math.pi * cutoff_hz / SAMPLE_RATE)
    first = second = 0.0
    softened: Track = []
    for value in track:
        first += alpha * (value - first)
        second += alpha * (first - second)
        softened.append(second)
    return softened


def overlay(*layers: tuple[Track, float, float]) -> Track:
    """Chồng các lớp `(track, gain, giây bắt đầu)`. Mỗi lớp được đưa về đỉnh 1 trước khi nhân
    gain, nên gain là tỉ lệ nghe được giữa các lớp chứ không phụ thuộc lớp đó vốn to hay nhỏ."""
    length = max(len(track) + frames_for(offset) for track, _gain, offset in layers)
    mixed: Track = [0.0] * length
    for track, gain, offset in layers:
        top = max((abs(value) for value in track), default=1.0) or 1.0
        start = int(SAMPLE_RATE * offset)
        for position, value in enumerate(track):
            mixed[start + position] += gain * value / top
    return mixed


def echo(track: Track, delay_seconds: float, gain: float) -> Track:
    """Vang phòng ngắn: dội lại sau `delay_seconds`, mỗi lần dội nhỏ đi `gain`, giữ hai lần."""
    delay = frames_for(delay_seconds)
    voiced: Track = track + [0.0] * (2 * delay)
    for position in range(delay, len(voiced)):
        voiced[position] += gain * voiced[position - delay]
    return voiced


def to_pcm(track: Track, peak: float) -> bytes:
    """Chuẩn hoá đỉnh về `peak`, vuốt 5 ms cuối về đúng 0 (khỏi "cạch"), đóng gói 16-bit."""
    top = max((abs(value) for value in track), default=1.0) or 1.0
    fade = frames_for(0.005)
    last = len(track) - 1
    frames = bytearray()
    for position, value in enumerate(track):
        tail = min(1.0, (last - position) / fade)
        frames += struct.pack("<h", int(32767 * peak * tail * value / top))
    return bytes(frames)
