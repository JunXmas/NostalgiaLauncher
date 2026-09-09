"""Phản hồi CurseForge giả (một mod Sodium, một file) dùng chung cho test lõi và test cầu nối."""

from __future__ import annotations

SEARCH_BODY = {
    "data": [
        {
            "id": 394468,
            "name": "Sodium",
            "slug": "sodium",
            "summary": "Nhanh",
            "authors": [{"name": "jellysquid3"}],
            "logo": {"thumbnailUrl": "https://x/icon.png"},
            "downloadCount": 12345,
            "latestFilesIndexes": [{"modLoader": 4}, {"modLoader": 6}],
        }
    ],
    "pagination": {"index": 0, "totalCount": 7},
}
FILES_BODY = {
    "data": [
        {
            "id": 8793729,
            "modId": 394468,
            "displayName": "Sodium 0.9.2",
            "fileName": "sodium+mc26.2.jar",
            "releaseType": 2,
            "hashes": [{"value": "b" * 40, "algo": 1}],
            "fileDate": "2026-01-01",
            "fileLength": 999,
            "downloadUrl": None,
            "gameVersions": ["26.2", "Fabric"],
            "dependencies": [{"modId": 306612, "relationType": 3}],
        }
    ]
}
