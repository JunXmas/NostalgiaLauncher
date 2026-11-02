"""Tham số OAuth của client Ely.by lấy từ đường dẫn chuyển hướng chính chủ."""

from urllib.parse import parse_qsl, urlencode, urlsplit

from nostalgia.errors import AccountError


def resolve_ely_authorization_query(authorize_url: str, account_root: str) -> str:
    """Giữ tham số opaque, thêm client_id bị frontend tách vào route /oauth2/v1/ely."""
    target, origin = urlsplit(authorize_url), urlsplit(account_root)
    prefix = origin.path.rstrip("/")
    if (
        target.scheme != origin.scheme
        or target.netloc.casefold() != origin.netloc.casefold()
        or target.username is not None
        or target.path not in (prefix + "/oauth2/v1/ely", prefix + "/api/oauth2/v1/ely")
    ):
        raise AccountError("Ely.by returned an unexpected authorization redirect.")
    fields = parse_qsl(target.query, keep_blank_values=True)
    client_ids = [value for key, value in fields if key == "client_id"]
    if client_ids and client_ids != ["ely"]:
        raise AccountError("Ely.by returned an unexpected authorization client.")
    if not client_ids:
        fields.append(("client_id", "ely"))
    # ely.by phát scope cách bằng dấu phẩy; API OAuth chỉ nhận dấu cách (RFC 6749 §3.3),
    # còn phẩy thì trả invalid_scope → không phát mã. Frontend của họ tự đổi, ta cũng phải đổi.
    fields = [(k, " ".join(v.replace(",", " ").split()) if k == "scope" else v) for k, v in fields]
    return urlencode(fields)
