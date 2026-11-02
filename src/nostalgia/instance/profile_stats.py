"""Cộng số liệu cục bộ của các bản chơi; không gửi lịch sử lên dịch vụ hồ sơ."""

from dataclasses import dataclass

from nostalgia.errors import NostalgiaError
from nostalgia.instance.stats import count_worlds, format_playtime, load_play_stats
from nostalgia.instance.store import game_dir_of, list_instances
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.storage.paths import DataPaths


@dataclass(frozen=True, slots=True)
class ProfileStats:
    total_seconds: int = 0
    launch_count: int = 0
    world_count: int = 0
    instance_count: int = 0
    favorite_version: str = ""

    @property
    def playtime_text(self) -> str:
        return format_playtime(self.total_seconds)


def load_profile_stats(paths: DataPaths) -> ProfileStats:
    instances = list_instances(paths)
    seconds = launches = worlds = 0
    versions: dict[str, int] = {}
    seen_directories: set[str] = set()
    repository = VersionRepository(paths)
    for instance in instances:
        play = load_play_stats(paths, instance.instance_id)
        seconds += play.total_seconds
        launches += play.launch_count
        game_dir = game_dir_of(paths, instance)
        if str(game_dir.resolve()) not in seen_directories:
            seen_directories.add(str(game_dir.resolve()))
            worlds += count_worlds(game_dir)
        try:
            version_meta = repository.load_version_meta(instance.version_id)
            game_version = version_meta.jar_owner_id
        except NostalgiaError:
            game_version = instance.version_id
        versions[game_version] = versions.get(game_version, 0) + play.total_seconds
    favorite = max(sorted(versions), key=lambda version_id: versions[version_id]) if seconds else ""
    return ProfileStats(seconds, launches, worlds, len(instances), favorite)
