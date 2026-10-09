"""Lưu bản xem trước đã chốt; kết quả phân biệt skin/cape khi dịch vụ lỗi một phần."""

from pathlib import Path

from PySide6.QtCore import QUrl

from nostalgia.api import Account, Launcher
from nostalgia.errors import NostalgiaError
from nostalgia.ui.appearance_draft import AppearanceDraft, AppearanceResult


def save_selection(
    launcher: Launcher,
    account: Account,
    draft: AppearanceDraft,
    skin_dirty: bool,
    cape_dirty: bool,
) -> AppearanceResult:
    skin_saved = cape_saved = False
    error = ""
    try:
        if skin_dirty:
            launcher.save_skin_selection(
                account, Path(QUrl(draft.source).toLocalFile()), slim=draft.slim
            )
            skin_saved = True
        if cape_dirty:
            launcher.set_cape(account, draft.cape_id)
            cape_saved = True
    except (NostalgiaError, OSError) as failure:
        error = str(failure)
    except Exception:
        error = "Chưa lưu được diện mạo. Hãy thử lại."
    return AppearanceResult(draft, skin_saved, cape_saved, error)
