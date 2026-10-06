"""Free báo lỗi được chứng minh bởi metadata; trường hợp chưa hiểu luôn ghi chưa xác minh."""

from __future__ import annotations

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
    versions = {
        "minecraft": game_version,
        "java": str(java_major),
        "fabricloader"
        if loader_kind == "fabric"
        else "quilt_loader"
        if loader_kind == "quilt"
        else loader_kind: loader_version,
    }
    reserved = {"minecraft", "java", "fabricloader", "forge", "neoforge", "quilt_loader"}
    owners: dict[str, str] = {}
    for archive in archives:
        if archive.problem:
            findings.append(ModFinding("unknown", archive.file_name, "", archive.problem))
        for descriptor in archive.descriptors:
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
                if mod_id in owners and owners[mod_id] != archive.file_name:
                    findings.append(
                        ModFinding(
                            "duplicate",
                            archive.file_name,
                            mod_id,
                            "Trùng mã mod với " + owners[mod_id],
                        )
                    )
                owners[mod_id], versions[mod_id] = archive.file_name, descriptor.version_number
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
        for descriptor in archive.descriptors:
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
                accepted = matches_any(installed, dependency.predicates)
                if accepted is None:
                    findings.append(
                        ModFinding(
                            "unknown",
                            archive.file_name,
                            dependency.mod_id,
                            "Chưa hỗ trợ khoảng phiên bản: " + " | ".join(dependency.predicates),
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
                            + installed
                            + " không khớp "
                            + " | ".join(dependency.predicates),
                        )
                    )
    return ModScan(game_version, loader_kind, loader_version, java_major, archives, tuple(findings))
