"""Install a compatible dependency closure as a batch; no hot reload or manual jar overwrite."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from nostalgia.errors import ServerError
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.server.compatibility import folia_supported
from nostalgia.server.content_catalog import ServerContentCatalog
from nostalgia.server.content_model import InstalledServerContent, ServerContentVersion
from nostalgia.server.download import download_jar
from nostalgia.server.model import DedicatedServer
from nostalgia.server.store import jar_digest, owned_path
from nostalgia.storage.atomic_bytes import atomic_write


def installed_content(directory: Path) -> tuple[InstalledServerContent, ...]:
    metadata = owned_path(directory, ".nostalgia-content.json")
    try:
        if metadata.exists() and metadata.stat().st_size > 256_000:
            raise ServerError("Metadata plugin/mod vượt giới hạn.")
        records = json.loads(metadata.read_text()) if metadata.exists() else []
        known = tuple(InstalledServerContent(**row) for row in records)
    except (ValueError, TypeError) as error:
        raise ServerError("Không đọc được danh sách plugin/mod đã cài.") from error
    result = list(known)
    for folder, content_kind in (("plugins", "plugin"), ("mods", "mod")):
        folder_dir = owned_path(directory, folder)
        if not folder_dir.exists():
            continue
        for path in sorted(folder_dir.glob("*.jar")):
            owned_path(directory, folder + "/" + path.name)
            if not any(
                row.content_kind == content_kind and row.file_name == path.name for row in known
            ):
                result.append(
                    InstalledServerContent(
                        "manual", "", "", path.name, content_kind, jar_digest(path)
                    )
                )
    return tuple(result)


def install_content(
    http_client: HttpClient,
    content_catalog: ServerContentCatalog,
    directory: Path,
    server: DedicatedServer,
    content_kind: str,
    content_version: ServerContentVersion,
    cancel_token: CancelToken | None = None,
    before_commit: Callable[[], object] | None = None,
) -> tuple[InstalledServerContent, ...]:
    existing = installed_content(directory)
    selected: list[ServerContentVersion] = []
    visiting: set[str] = set()

    def visit(candidate: ServerContentVersion) -> None:
        if len(selected) + len(visiting) >= 32:
            raise ServerError("Dependency vượt giới hạn 32 dự án.")
        if any(
            v.project_id == candidate.project_id and v.version_id == candidate.version_id
            for v in selected
        ):
            return
        present = next(
            (
                row
                for row in existing
                if row.source == candidate.source and row.project_id == candidate.project_id
            ),
            None,
        )
        if present:
            path = owned_path(
                directory,
                ("plugins" if present.content_kind == "plugin" else "mods")
                + "/"
                + present.file_name,
            )
            if (
                present.version_id == candidate.version_id
                and path.is_file()
                and jar_digest(path) == present.sha256
            ):
                return
            raise ServerError(
                "Dự án đã cài bản khác hoặc file bị sửa. Gỡ bản cũ trước khi cài bản mới."
            )
        if candidate.project_id in visiting or any(
            v.project_id == candidate.project_id for v in selected
        ):
            raise ServerError("Dependency có vòng lặp hoặc yêu cầu các bản xung đột.")
        visiting.add(candidate.project_id)
        for dependency in candidate.dependencies:
            visit(content_catalog.dependency(server, content_kind, dependency))
        visiting.remove(candidate.project_id)
        selected.append(candidate)

    visit(content_version)
    folder = "plugins" if content_kind == "plugin" else "mods"
    target_dir = owned_path(directory, folder)
    target_dir.mkdir(exist_ok=True)
    metadata = owned_path(directory, ".nostalgia-content.json")
    added: list[InstalledServerContent] = []
    written: list[Path] = []
    with tempfile.TemporaryDirectory(prefix=".install-", dir=directory) as staging:
        stage_dir = Path(staging)
        for candidate in selected:
            if (
                not candidate.file_name.endswith(".jar")
                or "/" in candidate.file_name
                or "\\" in candidate.file_name
            ):
                raise ServerError("Tên file plugin/mod không hợp lệ.")
            target = owned_path(target_dir, candidate.file_name)
            if target.exists() or any(row.file_name == candidate.file_name for row in added):
                raise ServerError("File đã tồn tại. Không ghi đè plugin/mod chép tay.")
            path = stage_dir / candidate.file_name
            sha256 = download_jar(
                http_client,
                candidate.url,
                path,
                algorithm=candidate.algorithm,
                digest=candidate.digest,
                size=candidate.size,
                cancel_token=cancel_token,
            )
            if server.engine_id == "folia" and not folia_supported(path):
                raise ServerError(
                    "Plugin không khai báo folia-supported: true. Không cài lên Folia."
                )
            added.append(
                InstalledServerContent(
                    candidate.source,
                    candidate.project_id,
                    candidate.version_id,
                    candidate.file_name,
                    content_kind,
                    sha256,
                )
            )
        if cancel_token:
            cancel_token.raise_if_cancelled()
        if before_commit:
            before_commit()
        try:
            for record in added:
                target = owned_path(target_dir, record.file_name)
                (stage_dir / record.file_name).replace(target)
                written.append(target)
            managed = [row for row in existing if row.source != "manual"] + added
            atomic_write(metadata, json.dumps([asdict(row) for row in managed]).encode())
        except BaseException:
            for path in written:
                path.unlink(missing_ok=True)
            raise
    return tuple(added)


def remove_content(directory: Path, content_kind: str, file_name: str) -> None:
    record = next(
        (
            row
            for row in installed_content(directory)
            if row.content_kind == content_kind and row.file_name == file_name
        ),
        None,
    )
    if record is None:
        raise ServerError("Không tìm thấy plugin/mod đã cài.")
    folder = "plugins" if content_kind == "plugin" else "mods"
    path = owned_path(directory, folder + "/" + file_name)
    if not path.is_file() or jar_digest(path) != record.sha256:
        raise ServerError("File đã thay đổi; cần kiểm tra trước khi gỡ.")
    trash_dir = owned_path(directory, ".nostalgia/removed")
    trash_dir.mkdir(parents=True, exist_ok=True)
    destination = owned_path(trash_dir, file_name)
    if destination.exists():
        raise ServerError(
            "Bản gỡ trước còn trong .nostalgia/removed; hãy chuyển ra trước khi gỡ tiếp."
        )
    path.rename(destination)
    try:
        records = [
            asdict(row)
            for row in installed_content(directory)
            if row.source != "manual"
            and not (row.content_kind == content_kind and row.file_name == file_name)
        ]
        atomic_write(owned_path(directory, ".nostalgia-content.json"), json.dumps(records).encode())
    except BaseException:
        destination.rename(path)
        raise
