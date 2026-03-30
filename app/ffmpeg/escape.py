"""FFmpeg drawtext string escaping utilities.

FFmpeg drawtext uses ':' as key-value separator and has specific escape
rules for text values. This module centralises all escaping to avoid
shell injection and FFmpeg parse errors.
"""


def escape_drawtext(text: str) -> str:
    """Escape a string for safe use as a drawtext 'text=' value.

    FFmpeg drawtext escaping order matters:
    1. Backslash must be first (it is the escape character)
    2. Single-quote (used as filter value delimiter)
    3. Colon (used as filter option separator)
    """
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    # Newlines in drawtext cause parse errors; replace with space
    text = text.replace("\n", " ").replace("\r", "")
    return text


def format_duration(total_secs: int) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    h = total_secs // 3600
    m = (total_secs % 3600) // 60
    s = total_secs % 60
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"
