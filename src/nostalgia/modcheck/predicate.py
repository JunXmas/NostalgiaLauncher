"""Khoảng phiên bản số, SemVer và Maven; cú pháp chưa hỗ trợ trả None thay vì đoán."""

from __future__ import annotations

import re


def resolve_version(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\+[\w.-]+)?", value)
    return tuple(int(number or 0) for number in match.groups()) if match else None  # type: ignore[return-value]


def matches(version_number: str, predicate: str) -> bool | None:
    predicate = predicate.strip()
    if predicate in ("", "*", ">=0", "maven:[0,)"):
        return True
    version_parts = resolve_version(version_number)
    if version_parts is None:
        return None
    if predicate.startswith("maven:"):
        interval = predicate.removeprefix("maven:")
        exact = re.fullmatch(r"\[([0-9.]+)\]", interval)
        if exact:
            return version_parts == resolve_version(exact[1])
        bounds = re.fullmatch(r"([\[(])([0-9.]*),([0-9.]*)([\])])", interval)
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
            outcomes.append(
                version_parts[0] == int(wildcard[1])
                and (wildcard[2] is None or version_parts[1] == int(wildcard[2]))
            )
            continue
        match = re.fullmatch(r"(>=|<=|>|<|=|\^|~)?(\d+(?:\.\d+){0,2}(?:\+[\w.-]+)?)", clause)
        if not match or (wanted := resolve_version(match[2])) is None:
            return None
        operator = match[1] or "="
        if operator in ("^", "~"):
            precision = len(match[2].split("+")[0].split("."))
            upper = (
                (wanted[0], wanted[1] + 1, 0)
                if operator == "~" or wanted[0] == 0
                else (wanted[0] + 1, 0, 0)
            )
            if operator == "^" and wanted[:2] == (0, 0) and precision == 3:
                upper = (0, 0, wanted[2] + 1)
            if precision == 1:
                upper = (wanted[0] + 1, 0, 0)
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
