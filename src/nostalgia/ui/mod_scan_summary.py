"""Chỉ trình bày lỗi có bằng chứng trong log, không suy đoán từ metadata."""

from nostalgia.api import ModScan


def has_repair_evidence(scan: ModScan) -> bool:
    return any(
        diagnostic.code == "dependency" and bool(diagnostic.predicates)
        for diagnostic in scan.diagnostics
    )


def scan_note(scan: ModScan) -> str:
    count = sum(finding.source == "log" for finding in scan.findings)
    if not count:
        return "Chưa nhận diện được lỗi từ log gần nhất. Không đề xuất thay mod."
    if not has_repair_evidence(scan):
        return "Log ghi nhận lỗi mod, nhưng chưa đủ dữ liệu để chọn bản thay thế."
    return f"Log ghi nhận {count} lỗi mod."
