"""Khoảng phiên bản số, SemVer và Maven; cú pháp chưa hỗ trợ trả None thay vì đoán."""

from __future__ import annotations

import re

VersionKey = tuple[tuple[int, ...], int, tuple[tuple[int, int, str], ...]]


def resolve_version(value: str) -> VersionKey | None:
    """Khoá so sánh SemVer: số (bỏ 0 cuối), bản phát hành > prerelease, bỏ phần +build."""
    match = re.fullmatch(r"(\d+(?:\.\d+)*)(?:-([\w.-]*))?(?:\+[\w.+-]+)?", value)
    if not match:
        return None
    numbers = tuple(int(number) for number in match[1].split("."))
    while len(numbers) > 1 and numbers[-1] == 0:
        numbers = numbers[:-1]
    if match[2] is None:
        return numbers, 1, ()
    # "1.21.11-" là prerelease nhỏ nhất: Fabric dùng nó làm cận dưới bao cả bản rc/beta.
    return (
        numbers,
        0,
        tuple(
            (0, int(part), "") if part.isdigit() else (1, 0, part)
            for part in match[2].split(".")
            if part
        ),
    )


def _padded(version_key: VersionKey) -> tuple[int, int, int]:
    numbers = (*version_key[0], 0, 0)
    return numbers[0], numbers[1], numbers[2]


def _lowest(*numbers: int) -> VersionKey:
    return resolve_version(".".join(map(str, numbers)) + "-")  # type: ignore[return-value]


def matches(version_number: str, predicate: str) -> bool | None:
    predicate = predicate.strip()
    if predicate in ("", "*", ">=0", "maven:[0,)"):
        return True
    version_parts = resolve_version(version_number)
    if version_parts is None:
        return None
    if predicate.startswith("maven:"):
        interval = predicate.removeprefix("maven:")
        exact = re.fullmatch(r"\[([^,\]]+)\]", interval)
        if exact:
            return version_parts == resolve_version(exact[1])
        bounds = re.fullmatch(r"([\[(])([^,]*),([^,]*)([\])])", interval)
        if not bounds:
            return None
        left, minimum, maximum, right = bounds.groups()
        low, high = resolve_version(minimum), resolve_version(maximum)
        return (
            not minimum
            or (low is not None and (version_parts >= low if left == "[" else version_parts > low))
        ) and (
            not maximum
            or (
                high is not None
                and (version_parts <= high if right == "]" else version_parts < high)
            )
        )
    if "||" in predicate:
        outcomes = [matches(version_number, branch) for branch in predicate.split("||")]
        return True if True in outcomes else None if None in outcomes else False
    outcomes = []
    for clause in predicate.split():
        wildcard = re.fullmatch(r"(\d+)(?:\.(\d+))?\.(?:x|\*)", clause)
        if wildcard:
            parts = _padded(version_parts)
            outcomes.append(
                parts[0] == int(wildcard[1])
                and (wildcard[2] is None or parts[1] == int(wildcard[2]))
            )
            continue
        match = re.fullmatch(
            r"(>=|<=|>|<|=|\^|~)?(\d+(?:\.\d+)*(?:-[\w.-]*)?(?:\+[\w.+-]+)?)", clause
        )
        if not match or (wanted := resolve_version(match[2])) is None:
            return None
        operator = match[1] or "="
        if operator in ("^", "~"):
            precision = len(re.split(r"[-+]", match[2])[0].split("."))
            major, minor, patch = _padded(wanted)
            upper = (
                _lowest(major, minor + 1) if operator == "~" or major == 0 else _lowest(major + 1)
            )
            if operator == "^" and (major, minor) == (0, 0) and precision == 3:
                upper = _lowest(0, 0, patch + 1)
            if precision == 1:
                upper = _lowest(major + 1)
            outcomes.append(wanted <= version_parts < upper)
        else:
            outcomes.append(
                {
                    "=": version_parts == wanted,
                    ">=": version_parts >= wanted,
                    "<=": version_parts <= wanted,
                    ">": version_parts > wanted,
                    "<": version_parts < wanted,
                }[operator]
            )
    return all(outcomes) if outcomes else None


def matches_any(version_number: str, predicates: tuple[str, ...]) -> bool | None:
    outcomes = [matches(version_number, predicate) for predicate in predicates]
    return True if True in outcomes else None if None in outcomes else False
