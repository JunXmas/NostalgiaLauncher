"""Recognize explicit loader dependency failures, without guessing from stack traces."""

from __future__ import annotations

import re

from nostalgia.modcheck.model import LogDiagnostic

_IDENTIFIER = r"[a-zA-Z0-9_.-]{1,96}"
_FABRIC = re.compile(
    r"Mod '[^'\r\n]{1,160}' \((" + _IDENTIFIER + r")\) (\S{1,128}) "
    r"requires (.{1,240}?) of (?:mod )?'[^'\r\n]{1,160}' \((" + _IDENTIFIER + r")\)"
    r"[^\r\n]{0,300}(?:missing|wrong version|not present)",
    re.IGNORECASE,
)
_FORGE = re.compile(
    r"Mod ID: '(" + _IDENTIFIER + r")', Requested by: '(" + _IDENTIFIER + r")', "
    r"Expected range: '([^'\r\n]{1,256})'",
    re.IGNORECASE,
)
_NEOFORGE = re.compile(
    r"(?:Mod )?(" + _IDENTIFIER + r") requires (?:mod )?(" + _IDENTIFIER + r") "
    r"([^\r\n]{1,160})[\r\n]+\s*Currently,",
    re.IGNORECASE,
)
_RUNTIME = re.compile(
    r"(?:Mixin apply for mod |from mod )(" + _IDENTIFIER + r")[^\r\n]{0,240}(?:failed|FAILED)"
    r"|due to errors, provided by '(" + _IDENTIFIER + r")'",
    re.IGNORECASE,
)


def version_predicate(text: str) -> tuple[str, ...]:
    text = text.strip()
    if text.startswith("version "):
        text = text[8:]
    if text in ("any version", "any", "*"):
        return ("*",)
    if re.fullmatch(r"[\[(][0-9., ]+[\])]", text):
        return ("maven:" + text.replace(" ", ""),)
    suffixes = {
        " or later": ">=",
        " or newer": ">=",
        " or above": ">=",
        " or higher": ">=",
        " or earlier": "<=",
    }
    for suffix, operator in suffixes.items():
        if text.endswith(suffix):
            text = operator + text.removesuffix(suffix)
            break
    if re.fullmatch(r"(?:>=|<=|>|<|=|\^|~)?[0-9]+(?:\.[0-9x*]+){0,2}(?:\+[\w.-]+)?", text):
        return (text,)
    bounds = re.fullmatch(r"between ([0-9.]+) \(inclusive\) and ([0-9.]+) \(exclusive\)", text)
    return (">=" + bounds[1] + " <" + bounds[2],) if bounds else ()


def parse_log(text: str, source: str) -> tuple[LogDiagnostic, ...]:
    results = []
    # Strip terminal colour codes; keep parsing bounded independently of file length.
    text = re.sub(r"\x1b\[[0-9;]*m", "", text[-2097152:])
    for match in _FABRIC.finditer(text):
        mod_id, version_number, requirement, dependency = match.groups()
        results.append(
            LogDiagnostic(
                mod_id, dependency, version_predicate(requirement), version_number, source
            )
        )
    for match in _FORGE.finditer(text):
        dependency, mod_id, requirement = match.groups()
        results.append(
            LogDiagnostic(mod_id, dependency, version_predicate(requirement), "", source)
        )
    for match in _NEOFORGE.finditer(text):
        mod_id, dependency, requirement = match.groups()
        results.append(
            LogDiagnostic(mod_id, dependency, version_predicate(requirement), "", source)
        )
    for match in _RUNTIME.finditer(text):
        mod_id = match[1] or match[2]
        results.append(LogDiagnostic(mod_id, "", (), "", source, "runtime"))
    return tuple(dict.fromkeys(results))[:100]
