"""Tin tức và ghi chú phiên bản, lấy từ chính nguồn mà launcher chính thức dùng."""

from __future__ import annotations

import json
import re
import time
from html.parser import HTMLParser

import requests

from .paths import CACHE_DIR

BASE = "https://launchercontent.mojang.com"
NEWS_URL = f"{BASE}/news.json"
PATCH_URL = f"{BASE}/v2/javaPatchNotes.json"
CACHE_TTL = 6 * 3600
TIMEOUT = 25


def _cached(name: str, url: str, ttl: int = CACHE_TTL) -> dict:
    """Có bản mới thì lấy, không thì dùng cache — mở trang không phải chờ mạng."""
    path = CACHE_DIR / name
    if path.exists() and time.time() - path.stat().st_mtime < ttl:
        return json.loads(path.read_text())
    try:
        data = requests.get(url, timeout=TIMEOUT).json()
    except Exception:
        if path.exists():
            return json.loads(path.read_text())  # mất mạng: xài bản cũ còn hơn trắng
        raise
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


class _Stripper(HTMLParser):
    """Đổi HTML của ghi chú thành văn bản thuần, giữ xuống dòng và gạch đầu dòng."""

    BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "tr", "ul", "ol"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.parts.append("\n  • ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag in self.BLOCK:
            # Xuống dòng cả trước khối: nếu chỉ ngắt sau, tiêu đề <h1> sẽ dính
            # vào câu cuối của đoạn trước ("Happy mining!New Features").
            self.parts.append("\n")
        if tag in ("h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self) -> str:
        out = "".join(self.parts)
        out = re.sub(r"[ \t]+", " ", out)
        return re.sub(r"\n{3,}", "\n\n", out).strip()


def html_to_text(html: str) -> str:
    s = _Stripper()
    s.feed(html or "")
    return s.text


def fetch_news(limit: int = 30) -> list[dict]:
    entries = _cached("news.json", NEWS_URL).get("entries", [])
    return [
        {
            "title": e.get("title", ""),
            "category": e.get("category", ""),
            "date": e.get("date", ""),
            "text": e.get("text", ""),
            "url": e.get("readMoreLink", ""),
        }
        for e in entries[:limit]
    ]


def fetch_patch_notes(limit: int = 60) -> list[dict]:
    entries = _cached("patchnotes.json", PATCH_URL).get("entries", [])
    return [
        {
            "title": e.get("title", ""),
            "version": e.get("version", ""),
            "type": e.get("type", ""),
            "path": e.get("contentPath", ""),
        }
        for e in entries[:limit]
    ]


def fetch_patch_body(content_path: str) -> str:
    if not content_path:
        return ""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", content_path)[-80:]
    data = _cached(f"patch-{safe}.json", f"{BASE}/v2/{content_path}", ttl=30 * 24 * 3600)
    return html_to_text(data.get("body", ""))
