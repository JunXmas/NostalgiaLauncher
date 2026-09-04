"""Kho tài khoản trên đĩa: một file JSON, quyền 0600, ghi nguyên tử.

Ba luật, mỗi luật sinh ra từ một cách hỏng cụ thể:

- **Ghi nguyên tử, quyền 0600.** File này sẽ chứa vé đăng nhập Microsoft ở M2. Ghi thẳng vào
  đích mà mất điện giữa chừng là mất sạch tài khoản; để quyền mặc định là cho mọi tiến trình
  khác trên máy đọc được vé.
- **Một bản ghi hỏng không làm bay các bản ghi còn lại.** Bỏ đúng bản ghi hỏng, giữ phần
  còn lại, và ghi cảnh báo qua `logging` — lõi không được in ra màn hình.
- **File hỏng ở mức JSON thì BÁO LỖI, không coi như rỗng.** Coi như rỗng là con đường thẳng
  tới việc lần ghi sau xoá sạch tài khoản của người dùng.

Phần đọc/ghi tách hẳn khỏi phần sửa danh sách: `load_*`/`save_*` chạm đĩa, còn `upsert_*`,
`remove_*`, `find_*` là hàm thuần trên tuple. Nhờ vậy logic sửa danh sách test được mà không
cần thư mục tạm nào.
"""

from __future__ import annotations

import logging
from pathlib import Path

from nostalgia.account.model import Account
from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, read_json

FORMAT_VERSION = 1

logger = logging.getLogger(__name__)


def load_accounts(path: Path) -> tuple[Account, ...]:
    """Đọc kho tài khoản. Chưa có file thì trả về rỗng — đó không phải lỗi."""
    if not path.exists():
        return ()
    document = as_mapping(read_json(path))
    accounts: list[Account] = []
    for index, raw_account in enumerate(as_list(document.get("accounts"))):
        account = _parse_account(as_mapping(raw_account))
        if account is None:
            logger.warning("bỏ qua bản ghi tài khoản hỏng ở vị trí %d trong %s", index, path)
            continue
        accounts.append(account)
    return tuple(accounts)


def save_accounts(path: Path, accounts: tuple[Account, ...]) -> None:
    """Ghi cả kho. Quyền 0600 vì file này có thể chứa vé đăng nhập."""
    document: JsonValue = {
        "format": FORMAT_VERSION,
        "accounts": [
            {
                "player_name": account.player_name,
                "player_uuid": account.player_uuid,
                "account_kind": account.account_kind,
                "access_token": account.access_token,
            }
            for account in accounts
        ],
    }
    atomic_write_json(path, document, private=True)


def find_account(accounts: tuple[Account, ...], player_name: str) -> Account | None:
    """Tra theo tên, không phân biệt hoa thường — người dùng gõ tay tên này."""
    wanted = player_name.casefold()
    for account in accounts:
        if account.player_name.casefold() == wanted:
            return account
    return None


def upsert_account(accounts: tuple[Account, ...], account: Account) -> tuple[Account, ...]:
    """Thêm mới, hoặc thay tại chỗ nếu tên đã có. Giữ nguyên thứ tự.

    Thay tại chỗ chứ không xoá-rồi-thêm-cuối: thứ tự trong file là thứ tự người dùng thấy
    khi liệt kê, và một lần đăng nhập lại không nên làm tài khoản nhảy xuống cuối danh sách.
    """
    wanted = account.player_name.casefold()
    replaced = tuple(
        account if existing.player_name.casefold() == wanted else existing for existing in accounts
    )
    if any(existing.player_name.casefold() == wanted for existing in accounts):
        return replaced
    return (*accounts, account)


def remove_account(accounts: tuple[Account, ...], player_name: str) -> tuple[Account, ...]:
    """Bỏ một tài khoản. Không có thì trả về nguyên vẹn — người gọi tự quyết có báo hay không."""
    wanted = player_name.casefold()
    return tuple(account for account in accounts if account.player_name.casefold() != wanted)


def _parse_account(fields: dict[str, JsonValue]) -> Account | None:
    player_name = as_string(fields.get("player_name"))
    player_uuid = as_string(fields.get("player_uuid"))
    account_kind = as_string(fields.get("account_kind"))
    if not player_name or not player_uuid or not account_kind:
        return None
    return Account(
        player_name=player_name,
        player_uuid=player_uuid,
        account_kind=account_kind,
        access_token=as_string(fields.get("access_token")) or "",
    )
