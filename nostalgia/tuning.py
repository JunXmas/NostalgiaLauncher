"""Smart JVM auto-tuning cho Minecraft: chọn heap cố định + bộ Garbage Collector
hợp máy để bớt micro-stutter và giữ FPS ổn định.

Dùng thư viện chuẩn (os.cpu_count) thay cho psutil: không thêm dependency, chạy
mọi OS, và không phình bản đóng gói PyInstaller. Cấp phát RAM (max_memory_mb) do
launcher quyết (thanh trượt / auto theo RAM máy); module này lo phần cờ JVM.
"""
from __future__ import annotations

import os

# Bộ cờ G1GC "Aikar" — chuẩn cộng đồng Minecraft cho client < ~12GB heap. Đã kiểm
# nghiệm rộng rãi: giảm khựng GC, giữ pause thấp mà không cần máy mạnh.
_AIKAR_G1 = (
    "-XX:+UseG1GC",
    "-XX:+ParallelRefProcEnabled",
    "-XX:MaxGCPauseMillis=200",
    "-XX:+UnlockExperimentalVMOptions",
    "-XX:+DisableExplicitGC",
    "-XX:+AlwaysPreTouch",
    "-XX:G1NewSizePercent=30",
    "-XX:G1MaxNewSizePercent=40",
    "-XX:G1HeapRegionSize=8M",
    "-XX:G1ReservePercent=20",
    "-XX:G1HeapWastePercent=5",
    "-XX:G1MixedGCCountTarget=4",
    "-XX:InitiatingHeapOccupancyPercent=15",
    "-XX:G1MixedGCLiveThresholdPercent=90",
    "-XX:G1RSetUpdatingPauseTimePercent=5",
    "-XX:SurvivorRatio=32",
    "-XX:+PerfDisableSharedMem",
    "-XX:MaxTenuringThreshold=1",
)

# ZGC thế hệ mới: pause dưới 1ms, hợp máy khoẻ (nhiều nhân, nhiều RAM) và Java đủ
# mới. Java < 24 vẫn coi ZGenerational là experimental nên phải mở khoá TRƯỚC.
_ZGC = ("-XX:+UseZGC", "-XX:+ZGenerational", "-XX:+AlwaysPreTouch")


def cpu_threads() -> int:
    """Số luồng CPU logic; trả 4 nếu không hỏi được."""
    return os.cpu_count() or 4


def use_zgc(max_memory_mb: int, cores: int, java_major: int) -> bool:
    """ZGC generational chỉ đáng khi máy đủ khoẻ và Java đủ mới, kẻo overhead của
    ZGC lại phản tác dụng trên máy yếu."""
    return java_major >= 21 and cores >= 8 and max_memory_mb >= 6144


def jvm_flags(max_memory_mb: int, *, java_major: int = 17,
              cores: int | None = None) -> list[str]:
    """Cờ JVM tối ưu: heap CỐ ĐỊNH (Xms=Xmx, tránh JVM co giãn heap gây giật) +
    GC hợp máy (ZGC cho máy khoẻ/Java mới, ngược lại G1GC-Aikar).

    max_memory_mb được kẹp tối thiểu 512MB để không sinh cờ vô lý.
    """
    mem = max(512, int(max_memory_mb))
    cores = cores if cores and cores > 0 else cpu_threads()
    flags = [f"-Xms{mem}M", f"-Xmx{mem}M"]
    if use_zgc(mem, cores, java_major):
        if java_major < 24:  # 21..23: ZGenerational còn experimental -> mở khoá trước
            flags.append("-XX:+UnlockExperimentalVMOptions")
        flags += list(_ZGC)
    else:
        flags += list(_AIKAR_G1)
    return flags


def describe(max_memory_mb: int, *, java_major: int = 17,
             cores: int | None = None) -> str:
    """Một dòng mô tả lựa chọn (cho log / UI)."""
    cores = cores if cores and cores > 0 else cpu_threads()
    gc = "ZGC (generational)" if use_zgc(max(512, max_memory_mb), cores, java_major) else "G1GC (Aikar)"
    return f"{max_memory_mb}MB heap · {cores} threads · Java {java_major} → {gc}"
