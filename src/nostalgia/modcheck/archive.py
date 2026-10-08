"""Quét chỉ đọc, giới hạn metadata/JAR lồng; từ chối symlink và zip bomb."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

from nostalgia.errors import ContentError
from nostalgia.modcheck.metadata import parse_fabric, parse_forge
from nostalgia.modcheck.model import ModArchive, ModDescriptor


def hash_archive(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def archive_hashes(path: Path) -> tuple[str, str]:
    hashes = hashlib.sha256(), hashlib.sha512()
    with path.open("rb") as stream:
        while payload := stream.read(262144):
            for digest in hashes:
                digest.update(payload)
    return hashes[0].hexdigest(), hashes[1].hexdigest()


def read_member(archive: zipfile.ZipFile, name: str, maximum: int = 262144) -> bytes:
    try:
        information = archive.getinfo(name)
    except KeyError:
        return b""
    if information.file_size > maximum or information.flag_bits & 1:
        raise ContentError("Metadata hoặc JAR lồng vượt giới hạn.")
    return archive.read(information)


def read_descriptors(
    archive: zipfile.ZipFile, budget: list[int], depth: int = 0, loader_kind: str = ""
) -> tuple[ModDescriptor, ...]:
    if depth > 4:
        raise ContentError("Mod lồng sâu quá mức hỗ trợ.")
    if loader_kind in ("forge", "neoforge"):
        name = "META-INF/neoforge.mods.toml" if loader_kind == "neoforge" else "META-INF/mods.toml"
        if payload := read_member(archive, name):
            return parse_forge(payload, read_member(archive, "META-INF/MANIFEST.MF"), loader_kind)
    fabric = read_member(archive, "fabric.mod.json")
    if fabric:
        descriptors = list(parse_fabric(fabric))
        for reference in json.loads(fabric).get("jars", []):
            nested = read_member(archive, reference["file"], 8388608)
            budget[0] += len(nested)
            if not nested or budget[0] > 33554432:
                raise ContentError("Mod lồng thiếu hoặc vượt giới hạn 32 MB.")
            with zipfile.ZipFile(io.BytesIO(nested)) as embedded:
                descriptors.extend(read_descriptors(embedded, budget, depth + 1))
        return tuple(descriptors)
    for name, loader_kind in (
        ("META-INF/neoforge.mods.toml", "neoforge"),
        ("META-INF/mods.toml", "forge"),
    ):
        if payload := read_member(archive, name):
            return parse_forge(payload, read_member(archive, "META-INF/MANIFEST.MF"), loader_kind)
    raise ContentError("Không có metadata Fabric/Forge/NeoForge được hỗ trợ.")


def scan_archives(game_dir: Path, loader_kind: str = "") -> tuple[ModArchive, ...]:
    directory = game_dir / "mods"
    if directory.is_symlink():
        raise ContentError("Không quét thư mục mods là symlink.")
    paths = sorted(directory.glob("*.jar"))
    if len(paths) > 1000:
        raise ContentError("Bản chơi vượt giới hạn 1000 JAR.")
    archives = []
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 536870912:
            raise ContentError("JAR là symlink, không phải file thường hoặc vượt 512 MB.")
        digest, sha512 = archive_hashes(path)
        try:
            with zipfile.ZipFile(path) as archive:
                descriptors = read_descriptors(archive, [0], loader_kind=loader_kind)
            if any(
                not descriptor.version_number or len(descriptor.version_number) > 128
                for descriptor in descriptors
            ):
                raise ContentError("Không xác định được phiên bản mod.")
            archives.append(ModArchive(path.name, digest, descriptors, sha512=sha512))
        except (
            ValueError,
            KeyError,
            TypeError,
            zipfile.BadZipFile,
            ContentError,
            UnicodeError,
        ) as error:
            archives.append(
                ModArchive(path.name, digest, (), "Metadata không kiểm được: " + str(error), sha512)
            )
    return tuple(archives)
