"""Số tài khoản ủng hộ: ghim trong kho là nền, Worker đè được, Worker chết thì lùi về ghim.

Cả tính năng này chỉ có một đường hỏng đáng sợ: mã QR dựng ra một tài khoản KHÔNG PHẢI của
chủ dự án — hoặc vì Worker trả rác mà launcher vẫn tin, hoặc vì lùi sai chỗ. Nên test ở đây
đi theo đúng ba trạng thái ấy chứ không dừng ở "hàm chạy không ném".
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import BankAccount, Launcher
from nostalgia.donate.vietqr import vietqr_payload
from test_api import make_launcher

WORKER_ACCOUNT = {"bin": "970422", "number": "9988776655", "holder": "TRAN THI B"}


def make_donate_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    body: bytes | None,
    *,
    status: int = 200,
) -> Launcher:
    if body is not None:
        server_state.add("/donate", body, status=status)
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    return replace(
        launcher, endpoints=replace(launcher.endpoints, donate_account=server.url("/donate"))
    )


def test_pinned_account_needs_no_network_at_all(tmp_path: Path) -> None:
    """Không có fixture `server` ở đây là CỐ Ý: lưới chặn socket trong conftest sẽ ném nếu
    hàm này lỡ chạm mạng. Mã QR phải dựng được lúc máy offline, đó là cả lý do ghim số."""
    launcher = Launcher.for_data_dir(tmp_path)
    account = launcher.donate_account()

    from nostalgia.facade.donate import PINNED_ACCOUNT

    if not (PINNED_ACCOUNT.bin and PINNED_ACCOUNT.number):
        assert account is None, "chưa khai số tài khoản thì phải trả None, đừng dựng QR rỗng"
        return
    assert account == PINNED_ACCOUNT
    assert launcher.donate_qr() is not None


def test_worker_answer_overrides_the_pinned_account(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Đổi số tài khoản KHÔNG được bắt ra bản mới — đó là cả lý do có endpoint này."""
    launcher = make_donate_launcher(
        server, server_state, tmp_path, certificate_pair, json.dumps(WORKER_ACCOUNT).encode()
    )
    assert launcher.refresh_donate_account() == BankAccount("970422", "9988776655", "TRAN THI B")


def test_worker_down_falls_back_instead_of_raising(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Worker 500 là chuyện thường (deploy, hết hạn mức). Ném ra tận giao diện thì nút ủng hộ
    hiện lỗi đỏ trong khi số ghim sẵn vẫn quét được ngon lành."""
    launcher = make_donate_launcher(
        server, server_state, tmp_path, certificate_pair, b"bad gateway", status=502
    )
    assert launcher.refresh_donate_account() is None


def test_worker_answer_missing_a_field_is_refused_whole(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Tài khoản nửa vời (có số, thiếu mã ngân hàng) dựng ra mã QR mà app ngân hàng từ chối —
    tệ hơn hẳn việc lùi về số ghim vẫn quét được. Nhận nửa vời là hỏng im lặng."""
    half = {"number": "9988776655", "holder": "TRAN THI B"}
    launcher = make_donate_launcher(
        server, server_state, tmp_path, certificate_pair, json.dumps(half).encode()
    )
    assert launcher.refresh_donate_account() is None


def test_qr_encodes_the_account_it_was_handed_not_some_other_one(tmp_path: Path) -> None:
    """Đè số tài khoản xong mà QR vẫn vẽ số cũ thì tiền đi nhầm chỗ và không ai thấy.

    Hai phép so, vì một phép thôi thì lọt: lưới phải khớp TỪNG Ô với chuỗi VietQR của đúng
    tài khoản được truyền vào, **và** phải khác lưới của một tài khoản khác — phép sau bắt
    được trường hợp façade lờ tham số đi mà vẫn tình cờ ra đúng cỡ lưới.
    """
    from nostalgia.auth.qr import encode_qr

    launcher = Launcher.for_data_dir(tmp_path)
    account = BankAccount("970422", "9988776655", "TRAN THI B")
    other = BankAccount("970436", "1234567890", "NGUYEN VAN A")

    grid = launcher.donate_qr_code(account)
    assert grid.modules == encode_qr(vietqr_payload(account, launcher.donate_memo())).modules
    assert grid.modules != launcher.donate_qr_code(other).modules
    assert launcher.donate_qr(account) is not None


def test_worker_answer_without_a_bank_name_is_still_accepted(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """`bank` là tuỳ chọn, khác hẳn ba trường kia. Bắt buộc nó là tự tạo thêm một đường để
    cả câu trả lời bị từ chối vì thiếu một dòng chữ không ảnh hưởng gì tới mã QR."""
    launcher = make_donate_launcher(
        server, server_state, tmp_path, certificate_pair, json.dumps(WORKER_ACCOUNT).encode()
    )
    account = launcher.refresh_donate_account()
    assert account is not None and account.bank == ""


def test_the_bank_name_from_the_worker_reaches_the_account(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    named = {**WORKER_ACCOUNT, "bank": "MB Bank"}
    launcher = make_donate_launcher(
        server, server_state, tmp_path, certificate_pair, json.dumps(named).encode()
    )
    account = launcher.refresh_donate_account()
    assert account is not None and account.bank == "MB Bank"
