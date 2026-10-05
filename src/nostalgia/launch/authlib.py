"""authlib-injector: javaagent để game hỏi skin/phiên qua máy chủ Yggdrasil khác Mojang (Ely.by).

Jar tải từ trang chính thức theo `latest.json` (có sha256), kiểm băm trước khi dùng — đây là
mã chạy trong JVM game nên không được tin file tải về mù quáng. Đã có jar hợp lệ trên đĩa thì
không chạm mạng. Prefetch API root để game không phải gọi mạng lúc khởi động.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from nostalgia.auth.endpoints import DEFAULT_AUTH_ENDPOINTS, AuthEndpoints
from nostalgia.errors import IntegrityError, NostalgiaError
from nostalgia.model.json_value import as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import fetch_json
from nostalgia.storage.files import ensure_dir

MAX_JAR_BYTES = 8 * 1024 * 1024


def ensure_authlib_injector(
    http_client: HttpClient,
    injector_dir: Path,
    *,
    endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS,
) -> Path:
    """Đường dẫn jar đã kiểm băm. CHẠM MẠNG khi chưa có jar hoặc có bản mới."""
    ensure_dir(injector_dir)
    try:
        latest = as_mapping(
            fetch_json(http_client, endpoints.authlib_injector_latest_url, what="authlib-injector")
        )
        download_url = as_string(latest.get("download_url")) or ""
        expected = (as_string(as_mapping(latest.get("checksums")).get("sha256")) or "").lower()
    except NostalgiaError:
        existing = sorted(injector_dir.glob("authlib-injector-*.jar"))
        if existing:
            return existing[-1]
        raise
    jar_path = injector_dir / download_url.rsplit("/", 1)[-1]
    if jar_path.is_file() and _sha256(jar_path) == expected:
        return jar_path
    payload = http_client.fetch_bytes(download_url, max_bytes=MAX_JAR_BYTES)
    if hashlib.sha256(payload).hexdigest() != expected:
        message = "authlib-injector tải về không khớp sha256 — không dùng"
        raise IntegrityError(message)
    jar_path.write_bytes(payload)
    return jar_path


def authlib_jvm_arguments(
    jar_path: Path, api_root: str, prefetched_metadata: bytes | None = None
) -> tuple[str, ...]:
    """Cờ JVM đặt TRƯỚC mọi cờ khác của bản game."""
    arguments = [f"-javaagent:{jar_path}={api_root}"]
    if prefetched_metadata:
        encoded = base64.b64encode(prefetched_metadata).decode()
        arguments.append(f"-Dauthlibinjector.yggdrasil.prefetched={encoded}")
    return tuple(arguments)


def fetch_api_metadata(http_client: HttpClient, api_root: str) -> bytes | None:
    """JSON meta của máy chủ Yggdrasil để prefetch; lỗi mạng thì để game tự hỏi."""
    try:
        return http_client.fetch_bytes(api_root, max_bytes=64 * 1024)
    except NostalgiaError:
        return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
