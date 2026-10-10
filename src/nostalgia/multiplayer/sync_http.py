"""Yêu cầu manifest có ký phiên, tách khỏi đường truyền file để giữ nền relay."""

from nostalgia.errors import MultiplayerError
from nostalgia.net.http import HttpClient
from nostalgia.net.session_proof import proof_headers
from nostalgia.operations.cancellation import CancelToken


class SyncHttp:
    _http_client: HttpClient
    _session_token: str
    _base_url: str

    def _request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        *,
        body: bytes | None = None,
        max_bytes: int = 256_000,
        absent_ok: bool = False,
        cancel_token: CancelToken | None = None,
    ) -> bytes | None:
        if "Authorization" in headers:
            headers = {
                **headers,
                **proof_headers(self._session_token, method, self._base_url + path, body),
            }
        response = self._http_client.send(
            method,
            self._base_url + path,
            headers=headers,
            body=body,
            max_bytes=max_bytes,
            cancel_token=cancel_token,
        )
        if absent_ok and response.status == 404:
            return None
        if response.status in (401, 403):
            raise MultiplayerError(
                "Máy chủ từ chối: phiên Plus hoặc quyền chủ phòng không còn hợp lệ."
            )
        if not response.is_ok:
            raise MultiplayerError("Dịch vụ đồng bộ chưa sẵn sàng hoặc phòng đã đóng. Hãy thử lại.")
        return response.body
