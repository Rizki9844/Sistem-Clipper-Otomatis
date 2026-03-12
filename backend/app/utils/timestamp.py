"""
Timestamp Utilities
=====================
Parse, convert, and validate timestamps.
"""


def parse_timestamp(timestamp: str) -> float:
    """
    Parse various timestamp formats to seconds.

    Supports:
        "01:23:45.678" → 5025.678
        "23:45.678" → 1425.678
        "45.678" → 45.678
        "123" → 123.0
    """
    parts = timestamp.strip().split(":")

    if len(parts) == 3:
        hours, minutes, seconds = parts
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return float(minutes) * 60 + float(seconds)
    elif len(parts) == 1:
        return float(parts[0])
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")


def format_timestamp(seconds: float, include_ms: bool = True) -> str:
    """
    Format seconds to HH:MM:SS.mmm timestamp.

    Examples:
        5025.678 → "01:23:45.678"
        65.5 → "00:01:05.500"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    if include_ms:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    else:
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d}"


def format_duration_human(seconds: float) -> str:
    """
    Format seconds to human-readable duration.

    Examples:
        65 → "1m 5s"
        3723 → "1h 2m 3s"
        45 → "45s"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)


def validate_time_range(
    start: float,
    end: float,
    max_duration: float,
    min_clip: float = 5.0,
    max_clip: float = 300.0,
) -> tuple[float, float, bool]:
    """
    Validate and clamp a time range.

    Returns:
        (clamped_start, clamped_end, is_valid)
    """
    start = max(0.0, start)
    end = min(max_duration, end)

    duration = end - start

    is_valid = (
        start < end
        and duration >= min_clip
        and duration <= max_clip
    )

    return start, end, is_valid
