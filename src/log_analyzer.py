"""High-level log analysis entry point."""

from .log_parser import parse_log


def analyze_log(log_text: str, context_lines: int = 2) -> dict[str, object]:
    """Analyze a build log and return its extracted signals."""
    return parse_log(log_text, context_lines=context_lines)
