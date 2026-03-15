"""Formatting utilities for display values."""


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string.

    Examples:
        format_duration(0) -> "0s"
        format_duration(45) -> "45s"
        format_duration(125) -> "2m 5s"
        format_duration(3725) -> "1h 2m 5s"
    """
    if seconds < 0:
        seconds = 0
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def format_char_count(chars: int) -> str:
    """Format a character count with K/M suffixes.

    Examples:
        format_char_count(500) -> "500"
        format_char_count(1500) -> "1.5K"
        format_char_count(1000000) -> "1.0M"
    """
    if chars < 1000:
        return str(chars)
    elif chars < 1_000_000:
        value = chars / 1000
        return f"{value:.1f}K"
    else:
        value = chars / 1_000_000
        return f"{value:.1f}M"


def format_percentage(part: float, total: float) -> str:
    """Format a part/total ratio as a percentage string.

    Examples:
        format_percentage(4200, 39300) -> "10.7%"
        format_percentage(0, 0) -> "0.0%"
    """
    if total == 0:
        return "0.0%"
    pct = (part / total) * 100
    return f"{pct:.1f}%"
