"""Record verified CurseForge pack identity and offline JAR labels after overrides."""

from pathlib import Path

from nostalgia.content.installed import LedgerEntry, list_installed, load_ledger, save_ledger
from nostalgia.content.local_metadata import refresh_metadata
from nostalgia.content.model import ProjectVersion
from nostalgia.storage.files import sha1_of_file


def record_pack_inventory(game_dir: Path, resolved_versions: list[ProjectVersion]) -> None:
    directory = game_dir / "mods"
    ledger = load_ledger(directory)
    for project_version in resolved_versions:
        path = directory / project_version.file_name
        # An override may replace a downloaded mod. Associate a CurseForge
        # project only while the installed bytes still match that release.
        if (
            not path.is_file()
            or not project_version.file_sha1
            or sha1_of_file(path) != project_version.file_sha1
        ):
            continue
        ledger[project_version.project_id] = LedgerEntry(
            project_id=project_version.project_id,
            title="",
            version_id=project_version.version_id,
            version_number=project_version.version_number,
            file_name=project_version.file_name,
            source="curseforge",
        )
    if resolved_versions:
        save_ledger(directory, ledger)
    if directory.is_dir():
        refresh_metadata(directory, list_installed(game_dir, "mod"))
