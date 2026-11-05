"""Cửa vào thống kê tự nguyện; không kết nối dịch vụ tài khoản hoặc game."""

from dataclasses import dataclass

from nostalgia import __version__
from nostalgia.facade.context import LauncherContext
from nostalgia.model.usage import usage_sample
from nostalgia.usage.collector import UsageCollector
from nostalgia.usage.configuration import load_usage_configuration


@dataclass(frozen=True, slots=True)
class UsageOperations(LauncherContext):
    def usage_collector(self) -> UsageCollector:
        return UsageCollector(
            self.paths.config_dir, load_usage_configuration(), __version__, self.platform.os_name
        )

    def usage_payload_sample(self) -> str:
        return usage_sample(__version__)
