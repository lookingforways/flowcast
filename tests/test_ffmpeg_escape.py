"""Tests for FFmpeg drawtext escaping."""
from app.ffmpeg.escape import escape_drawtext, format_duration


def test_escape_colon():
    assert escape_drawtext("Hello: World") == "Hello\\: World"


def test_escape_single_quote():
    assert escape_drawtext("It's a test") == "It\\'s a test"


def test_escape_backslash():
    assert escape_drawtext("path\\to\\file") == "path\\\\to\\\\file"


def test_escape_combined():
    result = escape_drawtext("Ep 1: 'Special' \\Characters")
    assert "\\:" in result
    assert "\\'" in result
    assert "\\\\" in result


def test_escape_newlines():
    result = escape_drawtext("Line 1\nLine 2")
    assert "\n" not in result


def test_format_duration():
    assert format_duration(90) == "1:30"
    assert format_duration(3661) == "1:01:01"
    assert format_duration(45 * 60 + 30) == "45:30"
    assert format_duration(0) == "0:00"
