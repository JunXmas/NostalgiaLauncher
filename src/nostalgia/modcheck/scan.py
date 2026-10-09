"""Metadata gives client-side warnings, not a verdict that the game will fail."""

from __future__ import annotations

from nostalgia.modcheck.inventory import client_descriptors, version_choices
from nostalgia.modcheck.model import ModArchive, ModFinding, ModScan
from nostalgia.modcheck.predicate import matches_any


def build_scan(
    archives: tuple[ModArchive, ...],
    game_version: str,
    loader_kind: str,
    loader_version: str,
    java_major: int,
) -> ModScan:
    findings = []
    versions = version_choices(archives)
    versions.update(
        {
            "minecraft": (game_version,),
            "java": (str(java_major),),
            "fabricloader"
            if loader_kind == "fabric"
            else "quilt_loader"
            if loader_kind == "quilt"
            else loader_kind: (loader_version,),
        }
    )
    if loader_kind == "neoforge" and game_version == "1.20.1" and loader_version.startswith("47."):
        versions["forge"] = (loader_version,)
    reserved = {"minecraft", "java", "fabricloader", "forge", "neoforge", "quilt_loader"}
    owners: dict[str, str] = {}
    for archive in archives:
        if archive.problem:
            findings.append(ModFinding("unknown", archive.file_name, "", archive.problem))
        for descriptor in client_descriptors(archive):
            for mod_id in (descriptor.mod_id, *descriptor.provides):
                if mod_id in reserved:
                    findings.append(
                        ModFinding(
                            "unknown",
                            archive.file_name,
                            mod_id,
                            "Mã mod trùng thành phần game/loader.",
                        )
                    )
                    continue
                if mod_id != descriptor.mod_id or descriptor.embedded:
                    continue
                if mod_id in owners and owners[mod_id] != archive.file_name:
                    findings.append(
                        ModFinding(
                            "duplicate",
                            archive.file_name,
                            mod_id,
                            "Trùng mã mod với " + owners[mod_id],
                        )
                    )
                owners[mod_id] = archive.file_name
            if descriptor.loader_kind != loader_kind and not (
                loader_kind == "quilt" and descriptor.loader_kind == "fabric"
            ):
                findings.append(
                    ModFinding(
                        "loader",
                        archive.file_name,
                        descriptor.mod_id,
                        "Mod dành cho " + descriptor.loader_kind + ", bản chơi dùng " + loader_kind,
                    )
                )
    for archive in archives:
        for descriptor in client_descriptors(archive):
            if descriptor.embedded:
                continue
            for dependency in descriptor.dependencies:
                installed = versions.get(dependency.mod_id)
                if installed is None:
                    if dependency.relationship == "required":
                        findings.append(
                            ModFinding(
                                "missing",
                                archive.file_name,
                                dependency.mod_id,
                                "Thiếu phụ thuộc " + dependency.mod_id,
                            )
                        )
                    continue
                outcomes = [
                    matches_any(candidate, dependency.predicates) for candidate in installed
                ]
                accepted = True if True in outcomes else None if None in outcomes else False
                if dependency.relationship == "required" and accepted is True:
                    continue
                if dependency.relationship == "conflict" and accepted is False:
                    continue
                if accepted is None or len(installed) > 1:
                    findings.append(
                        ModFinding(
                            "unknown",
                            archive.file_name,
                            dependency.mod_id,
                            "Chưa xác minh lựa chọn mod lồng/khoảng phiên bản: "
                            + " | ".join(dependency.predicates),
                        )
                    )
                elif (dependency.relationship == "required" and not accepted) or (
                    dependency.relationship == "conflict" and accepted
                ):
                    findings.append(
                        ModFinding(
                            "version" if dependency.relationship == "required" else "conflict",
                            archive.file_name,
                            dependency.mod_id,
                            dependency.mod_id
                            + " "
                            + " / ".join(installed)
                            + " không khớp "
                            + " | ".join(dependency.predicates),
                        )
                    )
    return ModScan(game_version, loader_kind, loader_version, java_major, archives, tuple(findings))
