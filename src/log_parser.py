"""Parse common build-log formats without assuming a single log convention."""

from __future__ import annotations

import re
from pathlib import Path
from typing import BinaryIO, TextIO

_LEVEL_PATTERNS = {
    "ERROR": re.compile(r"\b(?:ERROR|FATAL|CRITICAL|SEVERE)\b", re.IGNORECASE),
    "WARNING": re.compile(r"\b(?:WARN(?:ING)?)\b", re.IGNORECASE),
    "INFO": re.compile(r"\bINFO\b", re.IGNORECASE),
    "DEBUG": re.compile(r"\bDEBUG\b", re.IGNORECASE),
}
_LEVEL_KEYS = {
    "ERROR": "errors",
    "WARNING": "warnings",
    "INFO": "info",
    "DEBUG": "debug",
}

_ERROR_PATTERNS = (
    ("ModuleNotFoundError", re.compile(r"\bModuleNotFoundError\b", re.IGNORECASE)),
    ("ImportError", re.compile(r"\bImportError\b", re.IGNORECASE)),
    ("SyntaxError", re.compile(r"\bSyntaxError\b", re.IGNORECASE)),
    ("TypeError", re.compile(r"\bTypeError\b", re.IGNORECASE)),
    ("NameError", re.compile(r"\bNameError\b", re.IGNORECASE)),
    (
        "DependencyInstallationError",
        re.compile(
            r"(?:No matching distribution found|Could not find a version that "
            r"satisfies|Failed to build (?:installable )?wheel|"
            r"error: subprocess-exited-with-error|pip install .* failed)",
            re.IGNORECASE,
        ),
    ),
    (
        "CompilationError",
        re.compile(
            r"(?:fatal error:|compilation terminated|"
            r"(?:^|\s)(?:gcc|g\+\+|clang|cl)(?:\.exe)?\s*:\s*error:|"
            r"\bcompilation error\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "TestFailure",
        re.compile(
            r"(?:\bFAILED\b.*(?:test|tests)|(?:^|\s)FAIL(?:ED)?\s*[:(]|"
            r"\b[1-9]\d* failed\b|AssertionError)",
            re.IGNORECASE,
        ),
    ),
    (
        "ConnectionError",
        re.compile(
            r"\b(?:ConnectionError|Connection refused|"
            r"MaxRetryError|Temporary failure in name resolution)\b",
            re.IGNORECASE,
        ),
    ),
)

_SUCCESS_PATTERN = re.compile(
    r"\b(?:build (?:was )?successful|build succeeded|"
    r"build completed successfully|all tests passed|"
    r"successfully built|successfully installed)\b",
    re.IGNORECASE,
)


def _read_uploaded_file(uploaded_file: BinaryIO | TextIO) -> str:
    content = uploaded_file.read()
    if isinstance(content, str):
        return content
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The uploaded file must contain UTF-8 text.") from exc


def read_log_file(source: object) -> str:
    """Read an uploaded file or a local .log/.txt path as UTF-8 text."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        name = path.name
    else:
        name = getattr(source, "name", None)
        path = None

    if not isinstance(name, str) or Path(name).suffix.lower() not in {".log", ".txt"}:
        raise ValueError("Only .log and .txt files are supported.")

    if path is not None:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("The uploaded file must contain UTF-8 text.") from exc
    if not hasattr(source, "read"):
        raise ValueError("Provide a .log/.txt file or a supported file path.")
    return _read_uploaded_file(source)


def parse_log(log_text: str, context_lines: int = 2) -> dict[str, object]:
    """Extract severity levels, likely failures, and nearby context from a log."""
    if not isinstance(log_text, str):
        raise TypeError("Log content must be a string.")
    if context_lines < 0:
        raise ValueError("context_lines must be zero or greater.")

    lines = log_text.splitlines()
    levels: dict[str, list[str]] = {
        "errors": [],
        "warnings": [],
        "info": [],
        "debug": [],
    }
    matches: list[tuple[int, str]] = []
    relevant_indexes: set[int] = set()
    success_marker_found = False

    for index, line in enumerate(lines):
        if not line.strip():
            continue
        if _SUCCESS_PATTERN.search(line):
            success_marker_found = True

        for level, pattern in _LEVEL_PATTERNS.items():
            if pattern.search(line):
                levels[_LEVEL_KEYS[level]].append(line)

        for error_type, pattern in _ERROR_PATTERNS:
            if pattern.search(line):
                matches.append((index, error_type))
                relevant_indexes.add(index)
                break

        if _LEVEL_PATTERNS["ERROR"].search(line):
            relevant_indexes.add(index)

    error_type = matches[0][1] if matches else (
        "BuildError" if levels["errors"] else None
    )
    failure_indexes = {
        index for index, _ in matches
    } | {
        index
        for index, line in enumerate(lines)
        if _LEVEL_PATTERNS["ERROR"].search(line)
    }
    for index in failure_indexes:
        relevant_indexes.update(
            range(max(0, index - context_lines), min(len(lines), index + context_lines + 1))
        )

    relevant_context = [
        {"line_number": index + 1, "text": lines[index]}
        for index in sorted(relevant_indexes)
    ]
    failure_lines = [lines[index] for index in sorted(failure_indexes)]
    has_errors = bool(failure_indexes)
    successful = success_marker_found and not has_errors

    return {
        "line_count": len(lines),
        **levels,
        "error_type": error_type,
        "failure_lines": failure_lines,
        "context": relevant_context,
        "has_errors": has_errors,
        "successful": successful,
    }
