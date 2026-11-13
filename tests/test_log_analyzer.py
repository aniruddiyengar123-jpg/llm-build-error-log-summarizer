from src.log_analyzer import analyze_log


def test_analyzer_returns_error_type_and_surrounding_context():
    result = analyze_log("step 1\nERROR: failed\nstep 3", context_lines=1)
    assert result["error_type"] == "BuildError"
    assert result["failure_lines"] == ["ERROR: failed"]
    assert [item["text"] for item in result["context"]] == [
        "step 1",
        "ERROR: failed",
        "step 3",
    ]


def test_analyzer_handles_large_logs():
    log = "\n".join(f"INFO: step {index}" for index in range(50000))
    result = analyze_log(log)
    assert result["line_count"] == 50000
    assert result["errors"] == []
