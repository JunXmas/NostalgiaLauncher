"""Lập kế hoạch tải `client.jar`."""

from __future__ import annotations

from mccore.model.download import DownloadTask
from mccore.storage.paths import DataPaths
from mccore.version.meta import VersionMeta


def plan_client_task(version_meta: VersionMeta, paths: DataPaths) -> DownloadTask | None:
    """Đích là `versions/<jar_owner_id>/<jar_owner_id>.jar`, không phải theo `version_id`.

    Bản của Fabric không có jar riêng: nó dùng jar của bản vanilla. Trỏ theo `version_id` là
    lỗi "không tìm thấy client.jar" rất khó truy, vì thư mục của bản Fabric vẫn tồn tại và
    chỉ thiếu đúng một file.
    """
    if version_meta.client is None:
        return None
    return version_meta.client.to_task(paths.version_jar(version_meta.jar_owner_id))
