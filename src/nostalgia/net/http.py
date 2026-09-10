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
import ssl
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from nostalgia import __version__
from nostalgia.errors import Cancelled, NetworkError
from nostalgia.operations.cancellation import CancelToken

# Header mặc định của MỌI request. User-Agent là bắt buộc về thực tế: GitHub API trả 403 cho
# request không có UA (bộ tự cập nhật từng "Không kiểm được" vì vậy), Modrinth cũng chặn; người
# gọi vẫn đè được bằng `headers=`.
DEFAULT_HEADERS: Mapping[str, str] = {
    "Accept-Encoding": "identity",
    "User-Agent": f"NostalgiaLauncher/{__version__}",
}

_TLS_LOCK = threading.Lock()
_TLS_CACHE: dict[str, ssl.SSLContext] = {}


def default_tls_context() -> ssl.SSLContext:
    """Context TLS mặc định dùng chung cho cả tiến trình, tạo MỘT lần dưới khoá.

    Nạp chứng chỉ hệ thống (`load_default_certs`) song song từ nhiều luồng từng làm CPython
    segfault trên CI: lúc mở cửa sổ, vài cầu nối cùng dựng `HttpClient` trong luồng nền. Một
    `SSLContext` dùng chung sau khi tạo là an toàn, và khỏi đọc lại kho chứng chỉ mỗi lần.
    """
    with _TLS_LOCK:
        context = _TLS_CACHE.get("default")
        if context is None:
            context = _TLS_CACHE["default"] = ssl.create_default_context()
        return context


# Kích thước khối đọc từ socket. Nhỏ hơn khối băm vì mạng chậm hơn đĩa rất nhiều.
STREAM_CHUNK_SIZE = 64 * 1024
MAX_REDIRECTS = 5
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

# Trần cho phản hồi nạp trọn vào bộ nhớ. Manifest lớn nhất của Mojang khoảng 1,3 MB, nên
# 32 MiB là rất thoáng; điều quan trọng là CÓ trần. Không có trần thì một máy chủ hỏng (hoặc
# bị chiếm) gửi mãi không dừng sẽ làm hết bộ nhớ.
DEFAULT_MAX_RESPONSE_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Một phản hồi đã đọc trọn, kèm mã trạng thái.

    Chỉ `send` trả về kiểu này. Các đường tải file không trả response ra ngoài, vì để nó
    lọt ra là buộc mọi tầng trên phải biết về `http.client`.
    """

    status: int
    body: bytes

    @property
    def is_ok(self) -> bool:
        return 200 <= self.status < 300


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
        self._tls_context = tls_context or default_tls_context()
        self._local = threading.local()
        # Giữ danh sách mọi kết nối đã mở để `close()` đóng được cả kết nối của luồng khác.
        self._connections: list[http.client.HTTPSConnection] = []
        self._lock = threading.Lock()

    def send(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        cancel_token: CancelToken | None = None,
    ) -> HttpResponse:
        """Gửi một request và đọc trọn phản hồi, **không ném lỗi khi mã trả về là 4xx**.

        Đây là khác biệt cố ý so với `stream` và `fetch_bytes`. Với đăng nhập Microsoft,
        **thân của phản hồi lỗi mới là dữ liệu**: 400 kèm `AADSTS70002` nghĩa là app Azure
        chưa bật public client, 401 kèm `XErr=2148916233` nghĩa là tài khoản chưa có hồ sơ
        Xbox, 403 nghĩa là app chưa được Microsoft duyệt, 404 nghĩa là tài khoản chưa mua
        game. Ném lỗi ở đây là vứt đi đúng thứ cần đọc, và người dùng nhận một thông báo
        vô nghĩa thay vì việc họ phải làm.

        Lỗi ĐƯỜNG TRUYỀN thì vẫn ném `NetworkError` — đó là hỏng thật, không phải dữ liệu.

        Không cần tự bỏ kết nối khi thân chưa đọc hết: khác `stream`, ở đây phản hồi được
        đọc một lần rồi đóng ngay trong khối `with`, và `http.client` tự lo phần còn lại.
        Đã thử tay: chặn `_discard` rồi gọi tiếp một request khác trên cùng kết nối vẫn ra
        kết quả đúng.
        """
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        host, path = _split(url)
        request_headers = {**DEFAULT_HEADERS, **(headers or {})}
        response = self._open_response(host, url, method, path, body, request_headers)
        try:
            with response:
                # Đọc dư một byte để phân biệt "vừa đúng trần" với "vượt trần".
                payload = response.read(max_bytes + 1)
                status = response.status
        except (http.client.HTTPException, OSError) as exc:
            self._discard(host)
            message = f"không gọi được {url}: {exc}"
            raise NetworkError(message) from exc

        if len(payload) > max_bytes:
            message = f"{url}: phản hồi vượt {max_bytes} byte, đã ngắt"
            raise NetworkError(message)
        return HttpResponse(status=status, body=payload)

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
        # Theo chuyển hướng có hạn: GitHub (gói cập nhật) trả 302 sang CDN. Mỗi bước đi qua
        # `_split` nên đích vẫn phải là https; quá hạn hoặc thiếu Location là lỗi, không lặp mãi.
        for _hop in range(MAX_REDIRECTS + 1):
            host, path = _split(url)
            response = self._open_response(host, url, "GET", path, None, dict(DEFAULT_HEADERS))
            if response.status not in REDIRECT_STATUSES:
                break
            location = response.getheader("Location") or ""
            with response:
                response.read()
            self._discard(host)
            if not location:
                message = f"{url} chuyển hướng {response.status} nhưng không có Location"
                raise NetworkError(message)
            url = urljoin(url, location)
        else:
            message = f"{url}: quá {MAX_REDIRECTS} lần chuyển hướng, đã dừng"
            raise NetworkError(message)

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

    def _open_response(
        self,
        host: str,
        url: str,
        method: str,
        path: str,
        body: bytes | None,
        headers: Mapping[str, str],
    ) -> http.client.HTTPResponse:
        """Gửi request và lấy đầu phản hồi, thử lại MỘT lần trên kết nối mới nếu kết nối
        giữ-sống cũ đã bị máy chủ đóng.

        Xảy ra thật: sau khi tải 700 MB, piston-meta đóng kết nối rảnh; lần gọi kế tiếp
        trên kết nối đó nhận "Remote end closed connection without response". Đó không phải
        lỗi mạng, chỉ là kết nối hết hạn — mở kết nối mới là xong.
        """
        for attempt in range(2):
            connection, reused = self._connection_for(host)
            try:
                connection.request(method, path, body=body, headers=dict(headers))
                return connection.getresponse()
            except (http.client.HTTPException, OSError) as exc:
                self._discard(host)
                # Kết nối dùng lại mà hỏng ngay lúc gửi / đọc đầu phản hồi thì gần như chắc
                # là nó đã chết trong lúc rảnh (RemoteDisconnected, reset, EBADF...): thử lại
                # một lần trên kết nối mới. Kết nối mới toanh mà hỏng thì là lỗi mạng thật.
                if attempt == 0 and reused:
                    continue
                message = f"không gọi được {url}: {exc}"
                raise NetworkError(message) from exc
        message = f"không gọi được {url}"  # không tới được: vòng trên luôn return hoặc raise
        raise NetworkError(message)

    def _connection_for(self, host: str) -> tuple[http.client.HTTPSConnection, bool]:
        """Kết nối bền cho `host` của luồng này, kèm cờ "đã dùng trước đó"."""
        cached: dict[str, http.client.HTTPSConnection] = getattr(self._local, "by_host", {})
        self._local.by_host = cached
        connection = cached.get(host)
        if connection is not None:
            return connection, True
        connection = http.client.HTTPSConnection(
            host, context=self._tls_context, timeout=self._timeout_seconds
        )
        cached[host] = connection
        with self._lock:
            self._connections.append(connection)
        return connection, False

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


def _check_status(url: str, status: int) -> None:
    if 300 <= status < 400:
        # 301/302/303/307/308 đã được `stream` theo tới đích; còn lại (vd 304) không có thân
        # để tải — đừng để một trang chuyển hướng lạ bị lưu thành file.
        message = f"{url} trả về chuyển hướng {status}, không tải được"
        raise NetworkError(message)
    if status != 200:
        message = f"{url} trả về mã {status}"
        raise NetworkError(message)
