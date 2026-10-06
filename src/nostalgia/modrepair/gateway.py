"""Plus kiểm quyền ở mỗi lần lập và áp phương án, không tin cờ local."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict
from urllib.parse import urlsplit

from nostalgia.errors import ContentError
from nostalgia.modcheck.model import ModScan
from nostalgia.model.json_value import JsonValue, as_integer, as_list, as_mapping, as_string
from nostalgia.modrepair.model import RepairChange, RepairPlan
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json


def scan_payload(scan: ModScan) -> bytes:
    fields = asdict(scan)
    del fields["findings"]
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def scan_hash(scan: ModScan) -> str:
    return hashlib.sha256(scan_payload(scan)).hexdigest()


class HttpRepairGateway:
    def __init__(self, base_url: str, access_token: str, http_client: HttpClient) -> None:
        parts = urlsplit(base_url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.path not in ("", "/")
            or parts.query
            or parts.fragment
        ):
            raise ContentError("Địa chỉ dịch vụ Plus không hợp lệ.")
        self._base_url, self._access_token, self._http_client = (
            base_url.rstrip("/"),
            access_token,
            http_client,
        )

    def _request(self, path: str, payload: bytes) -> JsonValue:
        response = self._http_client.send(
            "POST",
            self._base_url + path,
            body=payload,
            headers={
                "Authorization": "Bearer " + self._access_token,
                "Content-Type": "application/json",
            },
            max_bytes=262144,
        )
        if response.status in (401, 403):
            raise ContentError("Cần phiên Google hiện hành và quyền Plus để dùng phương án sửa.")
        if not response.is_ok:
            raise ContentError("Dịch vụ sửa mod chưa sẵn sàng hoặc phương án đã hết hạn.")
        return decode_json(response.body, what="phương án sửa mod")

    def fetch_plan(self, scan: ModScan) -> RepairPlan:
        fields = as_mapping(self._request("/v1/plus/repair", scan_payload(scan)))
        plan_id = as_string(fields.get("plan_id")) or ""
        digest = as_string(fields.get("scan_hash")) or ""
        expiry = as_integer(fields.get("expires_at")) or 0
        if (
            not re.fullmatch(r"[0-9a-f]{64}", plan_id)
            or digest != scan_hash(scan)
            or not time.time() < expiry <= time.time() + 1000
        ):
            raise ContentError("Phương án không khớp bộ mod đã quét.")
        changes = []
        for document in as_list(fields.get("changes")):
            change = as_mapping(document)
            operation = as_string(change.get("operation")) or ""
            file_name = as_string(change.get("file_name")) or ""
            sha256 = as_string(change.get("sha256")) or ""
            url = as_string(change.get("url")) or ""
            size = as_integer(change.get("size")) or 0
            sha512 = as_string(change.get("sha512")) or ""
            reason = as_string(change.get("reason")) or ""
            parts = urlsplit(url)
            if (
                not re.fullmatch(r"[^/\\\x00-\x1f]{1,150}\.jar", file_name)
                or file_name.startswith(".")
                or operation not in ("add", "disable")
            ):
                raise ContentError("Phương án chứa đường dẫn hoặc thao tác không an toàn.")
            if operation == "disable" and not any(
                archive.file_name == file_name and archive.sha256 == sha256
                for archive in scan.archives
            ):
                raise ContentError("Mod cần tắt không khớp dữ liệu quét.")
            if operation == "add" and (
                parts.scheme != "https"
                or parts.netloc != "cdn.modrinth.com"
                or not parts.path.startswith("/data/")
                or parts.query
                or parts.fragment
                or not re.fullmatch(r"[0-9a-f]{128}", sha512)
                or not 0 < size <= 67108864
            ):
                raise ContentError("Nguồn phụ thuộc hoặc hash không hợp lệ.")
            changes.append(RepairChange(operation, file_name, sha256, url, size, sha512, reason))
        if len(changes) > 100 or len({change.file_name.casefold() for change in changes}) != len(
            changes
        ):
            raise ContentError("Phương án có file trùng hoặc quá nhiều thay đổi.")
        unresolved = tuple(
            as_string(value) or "Chưa xác minh" for value in as_list(fields.get("unresolved"))
        )
        return RepairPlan(plan_id, digest, expiry, tuple(changes), unresolved)

    def authorize(self, plan: RepairPlan) -> None:
        if time.time() >= plan.expires_at:
            raise ContentError("Phương án hết hạn; hãy quét lại.")
        fields = as_mapping(
            self._request(
                "/v1/plus/repair/" + plan.plan_id + "/authorize",
                json.dumps({"scan_hash": plan.scan_hash}).encode(),
            )
        )
        if fields.get("authorized") is not True:
            raise ContentError("Máy chủ chưa cho phép áp phương án.")
