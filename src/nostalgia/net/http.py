"""Máy khách HTTP dựa trên `http.client` của thư viện chuẩn.

Vì sao không dùng `requests`: đo trên CDN thật, `requests` chạm trần ~65 file/s khi chạy
song song trong khi `http.client` đạt ~120 file/s và còn tăng theo số luồng. Chạy tuần tự
thì hai bên bằng nhau (102,5 so với 102,4 ms mỗi request), nên chênh lệch hoàn toàn đến từ
khả năng mở rộng: phần việc Python nặng hơn của `requests` bị dồn vào GIL. Chi tiết ở
docs/PERFORMANCE.md §2. Đổi lại, kho không có phụ thuộc runtime nào.

Mỗi luồng giữ MỘT kết nối bền và dùng lại cho nhiều request — đo được nhanh hơn 2-5 lần so
với mở kết nối mới mỗi file.
"""

from __future__ import annotations

import http.client
import json
import ssl
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from nostalgia.errors import Cancelled, DataFileError, IntegrityError, NetworkError
from nostalgia.model.json_value import JsonValue
from nostalgia.operations.cancellation import CancelToken

# Kích thước khối đọc từ socket. Nhỏ hơn khối băm vì mạng chậm hơn đĩa rất nhiều.
STREAM_CHUNK_SIZE = 64 * 1024

# Trần cho phản hồi nạp trọn vào bộ nhớ. Manifest lớn nhất của Mojang khoảng 1,3 MB, nên
# 32 MiB là rất thoáng; điều quan trọng là CÓ trần. Không có trần thì một máy chủ hỏng (hoặc
# bị chiếm) gửi mãi không dừng sẽ làm hết bộ nhớ.
DEFAULT_MAX_RESPONSE_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Thử lại bao nhiêu lần, chờ bao lâu, và tổng cộng không quá bao lâu.

    `total_deadline_seconds` là thứ `timeout` của socket KHÔNG cho: timeout chỉ áp cho mỗi
    lần đọc, nên một máy chủ nhỏ giọt một byte mỗi 29 giây sẽ treo vô hạn mà không lần đọc
    nào quá hạn.
    """

    attempts: int = 4
    initial_backoff_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    total_deadline_seconds: float = 300.0


DEFAULT_RETRY_POLICY = RetryPolicy()


class HttpClient:
    """Kết nối bền theo từng luồng. Dùng chung được giữa các luồng của một pool tải."""

    __slots__ = ("_connections", "_local", "_lock", "_timeout_seconds", "_tls_context")

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        tls_context: ssl.SSLContext | None = None,
    ) -> None:
        """`tls_context` chỉ để test dựng máy chủ HTTPS cục bộ với chứng chỉ tự ký.

        Mặc định là `ssl.create_default_context()` — xác minh chứng chỉ đầy đủ. Không có
        tham số này thì test buộc phải chọc vào biến riêng của lớp, hoặc phải đi ra Internet
        thật; cả hai đều tệ hơn một chỗ tiêm rõ ràng.
        """
        self._timeout_seconds = timeout_seconds
        self._tls_context = tls_context or ssl.create_default_context()
        self._local = threading.local()
        # Giữ danh sách mọi kết nối đã mở để `close()` đóng được cả kết nối của luồng khác.
        self._connections: list[http.client.HTTPSConnection] = []
        self._lock = threading.Lock()

    def stream(
        self,
        url: str,
        write: Callable[[bytes], None],
        *,
        expected_size: int | None = None,
        max_bytes: int | None = None,
        cancel_token: CancelToken | None = None,
    ) -> int:
        """Tải `url`, đẩy từng khối qua `write`, trả về số byte đã đẩy.

        Không trả về đối tượng response: để nó lọt ra ngoài là buộc mọi tầng trên phải biết
        về `http.client`. Một lần gọi là MỘT lần thử — việc thử lại do `retry` lo, vì chỉ
        người gọi biết cách bỏ đi phần đã ghi dở.

        `expected_size` và `max_bytes` đặt **trần cứng**, và trần là bắt buộc về nguyên tắc:
        đã đo, một máy chủ không công bố `Content-Length` mà gửi mãi khiến ta ghi 26 MB
        trong 10 giây rồi chỉ dừng vì timeout — tức là ghi tới khi hết đĩa.

        `cancel_token` được kiểm sau MỖI khối. Không kiểm trong vòng này thì nút dừng vô
        dụng: đã đo, huỷ giữa lúc tải bốn file 4 MB không dừng được file nào.
        """
        limit = expected_size if expected_size is not None else max_bytes
        host, path = _split(url)
        connection = self._connection_for(host)
        try:
            connection.request("GET", path, headers={"Accept-Encoding": "identity"})
            response = connection.getresponse()
        except (http.client.HTTPException, OSError) as exc:
            self._discard(host)
            message = f"không gọi được {url}: {exc}"
            raise NetworkError(message) from exc

        with response:
            _check_status(url, response.status)
            written = 0
            try:
                while chunk := response.read(STREAM_CHUNK_SIZE):
                    if cancel_token is not None and cancel_token.is_cancelled():
                        self._discard(host)
                        raise Cancelled
                    written += len(chunk)
                    if limit is not None and written > limit:
                        self._discard(host)
                        message = f"{url}: gửi hơn {limit} byte đã công bố, đã ngắt"
                        raise NetworkError(message)
                    write(chunk)
            except (http.client.HTTPException, OSError) as exc:
                self._discard(host)
                message = f"mất kết nối khi đang tải {url}: {exc}"
                raise NetworkError(message) from exc

            if response.length:
                # Còn thân phản hồi chưa đọc: dùng lại kết nối này thì request sau sẽ đọc
                # phần còn sót và hỏng theo cách rất khó truy. Bỏ kết nối, mở lại lần sau.
                self._discard(host)
        return written

    def fetch_bytes(
        self,
        url: str,
        *,
        max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        cancel_token: CancelToken | None = None,
    ) -> bytes:
        """Tải trọn nội dung vào bộ nhớ. Chỉ dùng cho file nhỏ như manifest JSON."""
        chunks: list[bytes] = []
        self.stream(url, chunks.append, max_bytes=max_bytes, cancel_token=cancel_token)
        return b"".join(chunks)

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_exception: object) -> None:
        """Đóng mọi kết nối bền khi ra khỏi khối `with`.

        Không đóng thì socket còn treo tới khi bộ thu gom rác chạy, và trong một tiến trình
        ngắn như lệnh CLI thì điều đó nghĩa là để lại kết nối nửa mở cho máy chủ Mojang.
        """
        self.close()

    def close(self) -> None:
        with self._lock:
            connections = list(self._connections)
            self._connections.clear()
        for connection in connections:
            connection.close()

    def _connection_for(self, host: str) -> http.client.HTTPSConnection:
        cached: dict[str, http.client.HTTPSConnection] = getattr(self._local, "by_host", {})
        self._local.by_host = cached
        connection = cached.get(host)
        if connection is None:
            connection = http.client.HTTPSConnection(
                host, context=self._tls_context, timeout=self._timeout_seconds
            )
            cached[host] = connection
            with self._lock:
                self._connections.append(connection)
        return connection

    def _discard(self, host: str) -> None:
        """Bỏ kết nối đã lỗi để lần thử sau dựng lại từ đầu."""
        cached: dict[str, http.client.HTTPSConnection] = getattr(self._local, "by_host", {})
        connection = cached.pop(host, None)
        if connection is None:
            return
        with self._lock:
            if connection in self._connections:
                self._connections.remove(connection)
        connection.close()


def retry[T](
    operation: Callable[[], T],
    *,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    cancel_token: CancelToken | None = None,
) -> T:
    """Chạy lại `operation` theo backoff nhân đôi, cho tới khi xong hoặc hết hạn.

    Chỉ thử lại `NetworkError` và `IntegrityError`: tải dở dang và file hỏng đều là tình
    huống nhất thời trên CDN. Mọi lỗi khác nổi lên ngay — thử lại một lỗi lập trình chỉ làm
    chậm việc phát hiện nó.
    """
    deadline = time.monotonic() + policy.total_deadline_seconds
    backoff = policy.initial_backoff_seconds
    last_error: Exception | None = None

    for attempt in range(1, policy.attempts + 1):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        try:
            return operation()
        except (NetworkError, IntegrityError) as exc:
            last_error = exc
            remaining = deadline - time.monotonic()
            if attempt == policy.attempts or remaining <= 0:
                break
            if cancel_token is not None and cancel_token.is_cancelled():
                raise Cancelled from exc
            time.sleep(min(backoff, remaining))
            backoff *= policy.backoff_multiplier

    message = f"thất bại sau {policy.attempts} lần thử: {last_error}"
    raise NetworkError(message) from last_error


def _check_status(url: str, status: int) -> None:
    if 300 <= status < 400:
        # Mojang và Fabric không chuyển hướng (đã dò thật). CurseForge, OptiFine và GitHub
        # thì có — khi nào chạm tới chúng thì thêm xử lý 3xx ở đây, đừng để thân của trang
        # chuyển hướng bị lưu thành file.
        message = f"{url} trả về chuyển hướng {status}, chưa hỗ trợ"
        raise NetworkError(message)
    if status != 200:
        message = f"{url} trả về mã {status}"
        raise NetworkError(message)


def _split(url: str) -> tuple[str, str]:
    """Tách URL thành (host, đường dẫn kèm truy vấn). Chỉ nhận https, không nhận userinfo."""
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        message = f"chỉ hỗ trợ https với host rõ ràng: {url!r}"
        raise NetworkError(message)
    if "@" in parts.netloc:
        # `https://ai-do:mat-khau@host/` là mẫu lừa đảo kinh điển: mắt người đọc phần trước
        # dấu @ tưởng là tên máy. Từ chối thẳng, kèm lý do, thay vì để nó hỏng ở tầng DNS
        # với một thông điệp không ai hiểu.
        message = f"URL không được chứa tên đăng nhập: {url!r}"
        raise NetworkError(message)
    path = parts.path or "/"
    return parts.netloc, f"{path}?{parts.query}" if parts.query else path


def fetch_json(http_client: HttpClient, url: str, *, what: str) -> JsonValue:
    """Tải một tài liệu JSON và nêu rõ *tài liệu nào* hỏng khi nó hỏng.

    `JSONDecodeError` trần chỉ nói dòng và cột; với ba nguồn JSON khác nhau (danh mục phiên
    bản, JSON phiên bản, hai tầng manifest bản Java) thì thông báo đó không đủ để lần ra.
    """
    payload = http_client.fetch_bytes(url)
    try:
        # json.loads khai trả `Any`; ép về JsonValue ngay tại biên để cái `Any` đó không
        # lan ra khắp nơi dùng sau.
        document: JsonValue = json.loads(payload)
    except json.JSONDecodeError as exc:
        message = f"{what} không phải JSON hợp lệ: {exc}"
        raise DataFileError(message) from exc
    return document
