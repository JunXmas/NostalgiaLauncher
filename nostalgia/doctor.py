"""Chẩn đoán một bản cài đặt: soi từng mắt xích của luồng khởi động.

Mở được cửa sổ game chỉ cho biết "chạy / không chạy". Bộ này nói rõ *chỗ nào*
hỏng — thiếu jar nào, sai hash file nào, natives có giải nén chưa, Java nào được
chọn, lệnh cuối cùng ra sao — nên khi phát triển launcher nó hữu ích hơn nhiều.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .accounts import LaunchIdentity
from .install import Installer, _sha1, rules_allow
from .launch import build_command, find_java

OK, WARN, FAIL = "ok", "warn", "fail"


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""
    lines: list[str] = field(default_factory=list)

    @property
    def mark(self) -> str:
        return {OK: "✓", WARN: "!", FAIL: "✗"}[self.status]


@dataclass
class Report:
    version_id: str
    checks: list[Check] = field(default_factory=list)
    command: list[str] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == FAIL)

    @property
    def warned(self) -> int:
        return sum(1 for c in self.checks if c.status == WARN)

    def text(self, *, show_command: bool = True) -> str:
        out = [f"Chẩn đoán {self.version_id}", ""]
        for c in self.checks:
            out.append(f"  {c.mark} {c.name}{': ' + c.detail if c.detail else ''}")
            out.extend(f"      {line}" for line in c.lines[:8])
            if len(c.lines) > 8:
                out.append(f"      … và {len(c.lines) - 8} dòng nữa")
        out.append("")
        if self.failed:
            out.append(f"{self.failed} lỗi, {self.warned} cảnh báo — chưa chạy được.")
        elif self.warned:
            out.append(f"Không có lỗi, {self.warned} cảnh báo.")
        else:
            out.append("Mọi mắt xích đều ổn.")
        if show_command and self.command:
            out += ["", "Lệnh sẽ chạy (access token đã che):", ""]
            out += [f"  {a}" for a in self.command]
        return "\n".join(out)


def _redact(cmd: list[str]) -> list[str]:
    out, skip = [], False
    for arg in cmd:
        if skip:
            out.append("<đã che>")
            skip = False
            continue
        out.append(arg)
        if arg in ("--accessToken", "--session"):
            skip = True
    return out


def diagnose(installer: Installer, version_id: str, *, memory_mb: int = 2048,
             java_path: str = "", verify_hashes: bool = False) -> Report:
    report = Report(version_id)
    add = report.checks.append

    # ---------- metadata ----------
    try:
        meta = installer.version_json(version_id)
    except Exception as e:  # noqa: BLE001
        add(Check("Metadata phiên bản", FAIL, str(e)))
        return report
    parent = meta.get("jar")
    detail = f"{meta.get('type', '?')}, mainClass {meta['mainClass'].split('.')[-1]}"
    if parent and parent != version_id:
        detail += f", kế thừa từ {parent}"
    add(Check("Metadata phiên bản", OK, detail))

    # ---------- java ----------
    needed = meta.get("javaVersion", {}).get("majorVersion", 8)
    if java_path:
        add(Check("Java", OK, f"dùng đường dẫn tự đặt: {java_path} (cần Java {needed})"))
        java = java_path
    else:
        try:
            java = find_java(needed)
            add(Check("Java", OK, f"Java {needed} tại {java}"))
        except RuntimeError as e:
            java = "/usr/bin/java"
            add(Check("Java", FAIL, str(e).splitlines()[0]))

    # ---------- client jar ----------
    jar = installer.client_jar(meta)
    if not jar.is_file():
        add(Check("Client jar", FAIL, f"thiếu {jar}"))
    else:
        size = jar.stat().st_size / 1024 / 1024
        add(Check("Client jar", OK, f"{jar.name}, {size:.1f} MB"))

    # ---------- libraries ----------
    paths = installer.library_paths(meta)
    missing = [p for p in paths if not p.is_file()]
    if missing:
        add(Check("Thư viện", FAIL, f"thiếu {len(missing)}/{len(paths)}",
                  [str(p) for p in missing]))
    else:
        add(Check("Thư viện", OK, f"đủ {len(paths)} jar trên classpath"))

    if verify_hashes:
        bad = []
        for lib in meta["libraries"]:
            entry = installer._artifact_of(lib)
            if not entry:
                continue
            _url, dest, sha = entry
            if sha and dest.is_file() and _sha1(dest) != sha:
                bad.append(str(dest))
        add(Check("Hash thư viện", FAIL if bad else OK,
                  f"{len(bad)} file sai hash" if bad else "khớp hết", bad))

    # ---------- natives ----------
    native_libs = [l for l in meta["libraries"]
                   if "natives" in l and rules_allow(l.get("rules"))]
    natives = installer.natives_dir(meta)
    extracted = sorted(p.name for p in natives.iterdir()) if natives.is_dir() else []
    if native_libs and not extracted:
        add(Check("Natives", FAIL, f"{len(native_libs)} gói khai báo nhưng chưa giải nén"))
    elif native_libs:
        add(Check("Natives", OK, f"{len(extracted)} file trong {natives.name}/", extracted))
    else:
        add(Check("Natives", OK, "phiên bản này không dùng natives rời"))

    # ---------- assets ----------
    index_id = meta["assetIndex"]["id"]
    index_file = installer.assets_dir / "indexes" / f"{index_id}.json"
    if not index_file.is_file():
        add(Check("Assets", FAIL, f"thiếu asset index {index_id}.json"))
    else:
        objects = json.loads(index_file.read_text())["objects"]
        absent = [h["hash"] for h in objects.values()
                  if not (installer.assets_dir / "objects" / h["hash"][:2] / h["hash"]).is_file()]
        if absent:
            add(Check("Assets", FAIL,
                      f"thiếu {len(absent)}/{len(objects)} file (index {index_id})"))
        else:
            add(Check("Assets", OK, f"đủ {len(objects)} file (index {index_id})"))

    # ---------- dựng lệnh ----------
    probe = LaunchIdentity("DiagnosticUser", "0" * 32, "0", "msa", demo=False)
    try:
        cmd = build_command(meta, installer, probe, java=java, max_memory_mb=memory_mb)
    except Exception as e:  # noqa: BLE001
        add(Check("Dựng lệnh", FAIL, str(e)))
        return report

    leftover = [a for a in cmd if "${" in a]
    add(Check("Dựng lệnh", FAIL if leftover else OK,
              f"còn {len(leftover)} placeholder chưa thay" if leftover
              else f"{len(cmd)} tham số, không sót placeholder", leftover))

    if meta["mainClass"] not in cmd:
        add(Check("mainClass", FAIL, "không có trong lệnh"))
    else:
        add(Check("mainClass", OK, meta["mainClass"]))

    report.command = _redact(cmd)
    return report
