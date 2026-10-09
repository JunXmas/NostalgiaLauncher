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
from nostalgia.net.session_proof import proof_headers


def scan_payload(scan: ModScan) -> bytes:
    fields = asdict(scan)
    del fields["findings"]
    fields["repair_policy"] = "log-confirmed"
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
                **proof_headers(self._access_token, "POST", self._base_url + path, payload),
            },
            max_bytes=262144,
        )
        if response.status in (401, 403):
            raise ContentError("Cần phiên Google hiện hành và quyền Plus để dùng phương án sửa.")
        if response.status == 429:
            raise ContentError("Bạn đang lập quá nhiều phương án. Chờ một phút rồi thử lại.")
        if not response.is_ok:
            raise ContentError("Dịch vụ sửa mod chưa sẵn sàng hoặc phương án đã hết hạn.")
        return decode_json(response.body, what="phương án sửa mod")

    def fetch_plan(self, scan: ModScan, selection: str = "") -> RepairPlan:
        document = json.loads(scan_payload(scan))
        if selection:
            if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,96}", selection):
                raise ContentError("Lựa chọn sửa mod không hợp lệ.")
            document["selection"] = selection
        fields = as_mapping(self._request("/v1/plus/repair", json.dumps(document).encode()))
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
            group_id = as_string(change.get("group_id")) or ""
            version_number = as_string(change.get("version_number")) or ""
            project_name = as_string(change.get("project_name")) or ""
            icon_url = as_string(change.get("icon_url")) or ""
            if (
                (group_id and not re.fullmatch(r"[a-zA-Z0-9_.-]{1,96}", group_id))
                or len(version_number) > 128
                or len(project_name) > 160
                or (
                    icon_url
                    and not re.fullmatch(
                        r"https://cdn\.modrinth\.com/data/[^\s?#]{1,400}", icon_url
                    )
                )
                or (selection and group_id != selection)
            ):
                raise ContentError("Thông tin mod đề xuất chưa hợp lệ.")
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
            changes.append(
                RepairChange(
                    operation,
                    file_name,
                    sha256,
                    url,
                    size,
                    sha512,
                    reason,
                    group_id,
                    version_number,
                    project_name,
                    icon_url,
                )
            )
        if len(changes) > 100 or len(
            {(change.group_id, change.operation, change.file_name.casefold()) for change in changes}
        ) != len(changes):
            raise ContentError("Phương án có file trùng hoặc quá nhiều thay đổi.")
        unresolved = tuple(
            as_string(value) or "Chưa xác minh" for value in as_list(fields.get("unresolved"))
        )
        partial = fields.get("partial", False)
        blocked_groups = tuple(
            as_string(value) or "" for value in as_list(fields.get("blocked_groups"))
        )
        if len(blocked_groups) > 100 or any(
            not re.fullmatch(r"[a-zA-Z0-9_.-]{1,96}", value) for value in blocked_groups
        ):
            raise ContentError("Danh sách mod chưa xác minh không hợp lệ.")
        if not isinstance(partial, bool) or partial != bool(selection):
            raise ContentError("Phương án không khớp mod đã chọn.")
        return RepairPlan(
            plan_id, digest, expiry, tuple(changes), unresolved, partial, blocked_groups
        )

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
