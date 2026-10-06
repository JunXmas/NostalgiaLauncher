"""Dữ liệu popup dự án: mô tả, bản phát hành và các bản chơi đã cài."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QTextDocument

from nostalgia.api import ContentTarget, Launcher
from nostalgia.content.model import Project, ProjectDetails, ProjectVersion
from nostalgia.errors import NostalgiaError


@dataclass(frozen=True, slots=True)
class ProjectCatalog:
    details: ProjectDetails
    versions: tuple[ProjectVersion, ...]
    targets: tuple[ContentTarget, ...]
    notice: str = ""


def fetch_project_catalog(launcher: Launcher, project: Project) -> ProjectCatalog:
    """Lấy dữ liệu mạng ở luồng nền; lỗi mô tả không chặn danh sách bản phát hành."""
    notice = ""
    try:
        details = launcher.fetch_content_details(project)
    except NostalgiaError:
        details = ProjectDetails(project.description, "markdown", "")
        notice = "Chưa tải được giới thiệu đầy đủ. Bạn vẫn có thể chọn phiên bản để cài."
    with launcher.make_http_client() as http_client:
        versions = launcher.fetch_versions(http_client, project.source, project.project_id)
    return ProjectCatalog(details, versions, build_content_targets(launcher), notice)


def build_content_targets(launcher: Launcher) -> tuple[ContentTarget, ...]:
    """Đích cài nội dung hợp lệ từ các bản chơi trên đĩa. Không chạm mạng."""
    targets = []
    for instance in launcher.list_instances():
        try:
            targets.append(launcher.describe_content_target(instance.instance_id))
        except NostalgiaError:
            continue  # Bản chơi chưa cài đủ metadata không phải đích cài nội dung hợp lệ.
    return tuple(targets)


def resolve_about_text(details: ProjectDetails) -> str:
    """Đọc Markdown/HTML thành văn bản; không chạy HTML hoặc tải ảnh nhúng trong popup."""
    document = QTextDocument()
    if details.body_format == "html":
        document.setHtml(details.body)
    else:
        document.setMarkdown(details.body)
    return document.toPlainText().replace("\ufffc", "").strip()
