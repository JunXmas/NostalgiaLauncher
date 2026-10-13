"""Plan an in-place update without overwriting personal configuration or custom mods."""

import zipfile
from dataclasses import dataclass
from pathlib import Path

from nostalgia.content.builtin_receipt import BuiltinReceipt, BundledFile
from nostalgia.errors import ContentError
from nostalgia.instance.sync_transaction import safe_sync_target
from nostalgia.modcheck.archive import read_member
from nostalgia.modcheck.metadata import parse_fabric
from nostalgia.storage.files import sha1_of_file

ARTIFACT_DIRECTORIES = frozenset({"mods", "resourcepacks", "shaderpacks"})


@dataclass(frozen=True, slots=True)
class PackChanges:
    copies: dict[str, str]
    removals: frozenset[str]
    receipt: BuiltinReceipt


def existing_variant(game_dir: Path, relative: str) -> str:
    target = safe_sync_target(game_dir, relative)
    if target.is_file():
        return relative
    if relative.split("/")[0] in ARTIFACT_DIRECTORIES:
        disabled = relative + ".disabled"
        if safe_sync_target(game_dir, disabled).is_file():
            return disabled
    return ""


def matches(path: Path, entry: BundledFile) -> bool:
    return path.is_file() and sha1_of_file(path) == entry.sha1


def plan_builtin_update(
    game_dir: Path, stage: Path, original: BuiltinReceipt, desired: BuiltinReceipt
) -> PackChanges:
    previous = {entry.identity: (path, entry) for path, entry in original.files.items()}
    copies: dict[str, str] = {}
    removals: set[str] = set()
    owned = dict(original.files)
    for relative, entry in desired.files.items():
        target = safe_sync_target(game_dir, relative)
        variant = existing_variant(game_dir, relative)
        # Configuration is a player setting, even when it originally came from the pack.
        if relative.split("/")[0] not in ARTIFACT_DIRECTORIES:
            if not target.exists():
                copies[relative] = relative
            continue
        old = previous.get(entry.identity)
        if old is not None:
            old_path, old_entry = old
            old_variant = existing_variant(game_dir, old_path)
            if not old_variant:
                # A deleted bundled mod stays deleted; disabling remains disabled as well.
                continue
            old_target = safe_sync_target(game_dir, old_variant)
            if old_path == relative and matches(old_target, entry):
                continue
            if not matches(old_target, old_entry):
                raise ContentError("Giữ mod bạn đã thay đổi; chưa thể cập nhật: " + old_path)
            destination = relative + (".disabled" if old_variant.endswith(".disabled") else "")
            if variant and variant != old_variant:
                raise ContentError("Mod tự thêm trùng với bản cập nhật: " + relative)
            copies[destination] = relative
            if old_variant != destination:
                removals.add(old_variant)
            owned.pop(old_path, None)
            owned[relative] = entry
        elif variant:
            if not matches(safe_sync_target(game_dir, variant), entry):
                raise ContentError("Giữ file bạn tự cài; chưa thể cập nhật: " + relative)
        else:
            copies[relative] = relative
            owned[relative] = entry
    check_duplicate_mods(game_dir, stage, copies, frozenset(removals))
    return PackChanges(copies, frozenset(removals), BuiltinReceipt(desired.version, owned))


def fabric_ids(path: Path) -> frozenset[str]:
    if path.is_symlink():
        raise ContentError("Mod tự thêm là symlink; chưa thể cập nhật.")
    try:
        with zipfile.ZipFile(path) as archive:
            payload = read_member(archive, "fabric.mod.json")
        return frozenset(mod.mod_id for mod in parse_fabric(payload)) if payload else frozenset()
    except (zipfile.BadZipFile, ValueError):
        return frozenset()


def check_duplicate_mods(
    game_dir: Path, stage: Path, copies: dict[str, str], removals: frozenset[str]
) -> None:
    incoming = {
        target: fabric_ids(stage / source)
        for target, source in copies.items()
        if target.startswith("mods/") and target.endswith(".jar")
    }
    if not incoming:
        return
    for path in (game_dir / "mods").glob("*.jar"):
        relative = path.relative_to(game_dir).as_posix()
        if relative in removals or relative in incoming:
            continue
        identifiers = fabric_ids(path)
        for target, wanted in incoming.items():
            if identifiers & wanted:
                raise ContentError(
                    "Mod tự cài trùng với bản cập nhật: " + path.name + " / " + Path(target).name
                )
