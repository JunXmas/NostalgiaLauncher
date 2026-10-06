"""Giới thiệu đầy đủ của dự án từ nguồn nội dung đang dùng."""

from __future__ import annotations

from nostalgia.content import curseforge, modrinth
from nostalgia.content.model import Project, ProjectDetails
from nostalgia.facade.context import LauncherContext
from nostalgia.settings.store import load_settings


class ContentDetailOperations(LauncherContext):
    __slots__ = ()

    def fetch_content_details(self, project: Project) -> ProjectDetails:
        """Giới thiệu đầy đủ từ nguồn của dự án. CHẠM MẠNG."""
        with self.make_http_client() as http_client:
            if project.source == "curseforge":
                return curseforge.fetch_project_details(
                    http_client,
                    load_settings(self.paths.config_dir).curseforge_api_key,
                    project,
                    endpoints=self.endpoints,
                )
            return modrinth.fetch_project_details(
                http_client,
                project.project_id,
                endpoints=self.endpoints,
            )
