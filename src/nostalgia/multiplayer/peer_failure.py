"""Phân biệt lỗi dịch vụ cấp quyền với lỗi đường truyền P2P; không lộ SDP/token."""

from nostalgia.errors import MultiplayerError


class PeerConnectionError(MultiplayerError):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


def negotiation_refusal(status: int, purpose: str) -> PeerConnectionError:
    if status == 404:
        return PeerConnectionError(
            "Phòng đã đóng hoặc lời mời đã hết hiệu lực. Hãy nhận lời mời mới.", retryable=False
        )
    if status in (401, 403):
        return PeerConnectionError(
            "Host đã khóa phòng hoặc quyền đồng bộ không còn hiệu lực. Nhờ host kiểm tra lại."
            if purpose == "sync"
            else "Host đã khóa phòng hoặc lời mời không còn hiệu lực. Nhờ host kiểm tra lại.",
            retryable=purpose == "game",
        )
    if status == 409:
        return PeerConnectionError("Host chưa sẵn sàng. Chờ host bật LAN rồi bấm Thử kết nối lại.")
    if status == 429:
        return PeerConnectionError("Phòng đang có nhiều yêu cầu. Chờ một lát rồi thử kết nối lại.")
    if status == 504:
        return PeerConnectionError(
            "Host chưa trả lời yêu cầu P2P. Nhờ host kiểm tra mạng và cập nhật launcher."
        )
    return PeerConnectionError("Dịch vụ kết nối phòng tạm thời không sẵn sàng. Hãy thử lại.")


def connection_failure(stage: str) -> PeerConnectionError:
    if stage == "signalling":
        return PeerConnectionError(
            "Không liên lạc được với dịch vụ kết nối phòng. Kiểm tra mạng rồi thử lại."
        )
    if stage == "gathering":
        return PeerConnectionError(
            "Không xác định được đường P2P. Kiểm tra VPN, tường lửa và kết nối mạng."
        )
    return PeerConnectionError(
        "Hai máy chưa nối được P2P. Mạng có thể chặn UDP hoặc NAT không hỗ trợ đường trực tiếp. "
        "Thử mạng khác rồi bấm Thử kết nối lại; relay dữ liệu đã tắt."
    )
