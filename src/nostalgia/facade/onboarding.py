"""Cho UI lưu lựa chọn liên kết Google qua façade; không cấp quyền Plus."""

from nostalgia.facade.context import LauncherContext
from nostalgia.model.json_value import as_mapping
from nostalgia.storage.files import atomic_write_json, read_json


class OnboardingOperations(LauncherContext):
    __slots__ = ()

    def load_google_link_reviewed(self) -> bool:
        path = self.paths.config_dir / "onboarding.json"
        return path.is_file() and as_mapping(read_json(path)).get("google_link_reviewed") is True

    def save_google_link_reviewed(self) -> None:
        atomic_write_json(self.paths.config_dir / "onboarding.json", {"google_link_reviewed": True})
