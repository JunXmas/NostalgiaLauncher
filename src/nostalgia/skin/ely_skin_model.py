"""Đổi dáng tay bằng form sửa skin của Ely.by, không đoán endpoint hoặc bỏ qua lỗi."""

from __future__ import annotations

import json
import re
from contextlib import suppress
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit

from nostalgia.auth.ely_web import FORM_CONTENT_TYPE, ElyWebSession, request_ely_web, web_json_body
from nostalgia.errors import AccountError
from nostalgia.model.json_value import JsonValue, as_mapping
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken


class _ModelForm(HTMLParser):
    def __init__(self, document: dict[str, JsonValue]) -> None:
        super().__init__()
        self.document = document
        self.action = self.method = ""
        self.fields: list[tuple[str, str]] = []
        self.inside = self.has_model = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form" and attributes.get("id") == "formEditSkin":
            self.inside = True
            self.action = attributes.get("action") or ""
            self.method = (attributes.get("method") or "POST").upper()
        if self.inside and tag in ("input", "select"):
            name = attributes.get("name") or ""
            if name == "is_slim":
                self.has_model = True
            elif name and attributes.get("type") not in (
                "submit",
                "button",
                "file",
                "radio",
                "checkbox",
            ):
                value = attributes.get("value") or ""
                current = self.document.get(name.removesuffix("[]"))
                if current is not None and (
                    not value or "{{" in value or attributes.get("al-value")
                ):
                    values = current if isinstance(current, list) else [current]
                    self.fields.extend(
                        (name, str(candidate))
                        for candidate in values
                        if isinstance(candidate, (str, int, float))
                    )
                    return
                if "{{" in value:
                    raise AccountError(
                        "Chưa đọc được form đổi dáng tay Ely.by. Skin đang mặc được giữ nguyên."
                    )
                self.fields.append((name, value))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.inside = False


def set_ely_skin_model(
    http_client: HttpClient,
    web_session: ElyWebSession,
    skin_id: int,
    slim: bool,
    *,
    cancel_token: CancelToken | None = None,
) -> None:
    headers = {"Cookie": web_session.site_cookies}
    response = request_ely_web(
        http_client,
        "GET",
        f"{web_session.endpoints.site_root}/skins/s{skin_id}",
        headers=headers,
        cancel_token=cancel_token,
        step="đọc dáng tay skin Ely.by",
    )
    text = response.body.decode("utf-8", errors="replace")
    match = re.search(r"alight\.service\.skin\s*=\s*", text)
    document = {}
    if match:
        with suppress(ValueError):
            document = as_mapping(json.JSONDecoder().raw_decode(text[match.end() :])[0])
    if document.get("is_slim") is slim:
        return
    response = request_ely_web(
        http_client,
        "GET",
        f"{web_session.endpoints.site_root}/skins/s{skin_id}/edit",
        headers=headers,
        cancel_token=cancel_token,
        step="đọc tùy chọn dáng tay Ely.by",
    )
    form = _ModelForm(document)
    form.feed(response.body.decode("utf-8", errors="replace"))
    address = urljoin(web_session.endpoints.site_root, form.action)
    if (
        not form.action
        or not form.has_model
        or form.method not in ("POST", "PUT", "PATCH")
        or urlsplit(address).netloc != urlsplit(web_session.endpoints.site_root).netloc
        or urlsplit(address).scheme != urlsplit(web_session.endpoints.site_root).scheme
    ):
        raise AccountError(
            "Ely.by chưa cho đổi dáng tay của skin này. Skin đang mặc được giữ nguyên."
        )
    fields = [(name, value) for name, value in form.fields if name != "is_slim"]
    fields.append(("is_slim", "1" if slim else "0"))
    response = request_ely_web(
        http_client,
        form.method,
        address,
        body=urlencode(fields).encode(),
        headers={**headers, "Content-Type": FORM_CONTENT_TYPE},
        cancel_token=cancel_token,
        step="đổi dáng tay skin Ely.by",
    )
    updated = web_json_body(response, step="đổi dáng tay skin Ely.by")
    model = as_mapping(updated.get("skin")) or updated
    if model.get("is_slim") not in ((True, 1, "1") if slim else (False, 0, "0")):
        raise AccountError("Ely.by chưa xác nhận dáng tay đã chọn. Skin đang mặc được giữ nguyên.")
