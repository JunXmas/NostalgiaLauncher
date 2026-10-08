"""Bản kê mod tối thiểu, không chứa thế giới, log hoặc đường dẫn cá nhân."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModDependency:
    mod_id: str
    predicates: tuple[str, ...]
    relationship: str = "required"


@dataclass(frozen=True, slots=True)
class ModDescriptor:
    mod_id: str
    version_number: str
    loader_kind: str
    dependencies: tuple[ModDependency, ...]
    provides: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModArchive:
    file_name: str
    sha256: str
    descriptors: tuple[ModDescriptor, ...]
    problem: str = ""
    sha512: str = ""


@dataclass(frozen=True, slots=True)
class LogDiagnostic:
    mod_id: str
    dependency_id: str
    predicates: tuple[str, ...]
    reported_version: str
    source: str
    code: str = "dependency"


@dataclass(frozen=True, slots=True)
class ModFinding:
    code: str
    file_name: str
    mod_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ModScan:
    game_version: str
    loader_kind: str
    loader_version: str
    java_major: int
    archives: tuple[ModArchive, ...]
    findings: tuple[ModFinding, ...]
    diagnostics: tuple[LogDiagnostic, ...] = ()
