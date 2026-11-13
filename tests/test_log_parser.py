from io import BytesIO

import pytest

from src.log_parser import parse_log, read_log_file


def test_read_pasted_log_string():
    log = "ERROR: build failed"
    assert parse_log(log)["errors"] == [log]


def test_read_uploaded_log_content():
    uploaded = BytesIO(b"INFO: build started")
    uploaded.name = "build.log"
    assert read_log_file(uploaded) == "INFO: build started"


def test_read_log_file_path(tmp_path):
    log_path = tmp_path / "build.txt"
    log_path.write_text("ERROR: compilation failed", encoding="utf-8")
    assert read_log_file(log_path) == "ERROR: compilation failed"


def test_empty_log_has_no_failures():
    result = parse_log("")
    assert result["line_count"] == 0
    assert result["errors"] == []
    assert result["successful"] is False


def test_extracts_levels_and_context():
    result = parse_log(
        "INFO starting\nWARNING: deprecated\n"
        "Traceback follows\nModuleNotFoundError: No module named 'demo'\n"
        "DEBUG details",
        context_lines=1,
    )
    assert result["warnings"] == ["WARNING: deprecated"]
    assert result["info"] == ["INFO starting"]
    assert result["debug"] == ["DEBUG details"]
    assert result["error_type"] == "ModuleNotFoundError"
    assert result["context"] == [
        {"line_number": 3, "text": "Traceback follows"},
        {
            "line_number": 4,
            "text": "ModuleNotFoundError: No module named 'demo'",
        },
        {"line_number": 5, "text": "DEBUG details"},
    ]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("ModuleNotFoundError: No module named 'requests'", "ModuleNotFoundError"),
        ("ImportError: cannot import name X", "ImportError"),
        ("SyntaxError: invalid syntax", "SyntaxError"),
        ("TypeError: unsupported operand", "TypeError"),
        ("NameError: name is not defined", "NameError"),
        ("ERROR: No matching distribution found for package", "DependencyInstallationError"),
        ("gcc: error: compilation terminated", "CompilationError"),
        ("FAILED tests/test_example.py::test_case", "TestFailure"),
        ("ConnectionError: connection refused", "ConnectionError"),
    ],
)
def test_identifies_common_failures(line, expected):
    assert parse_log(line)["error_type"] == expected


def test_detects_successful_build_even_with_warning():
    result = parse_log("WARNING: optional setting ignored\nBuild succeeded")
    assert result["successful"] is True
    assert result["has_errors"] is False


def test_zero_failed_tests_are_not_classified_as_a_failure():
    result = parse_log("18 passed, 0 failed\nBuild completed successfully")
    assert result["error_type"] is None
    assert result["successful"] is True


@pytest.mark.parametrize("filename", ["notes.csv", "build.exe", "no-extension"])
def test_rejects_unsupported_file_formats(filename):
    uploaded = BytesIO(b"text")
    uploaded.name = filename
    with pytest.raises(ValueError, match="Only .log and .txt"):
        read_log_file(uploaded)


def test_rejects_non_string_log_input():
    with pytest.raises(TypeError, match="must be a string"):
        parse_log(None)


def test_rejects_negative_context_size():
    with pytest.raises(ValueError, match="zero or greater"):
        parse_log("ERROR: bad", context_lines=-1)
