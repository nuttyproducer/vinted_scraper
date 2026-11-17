"""Listing-age helpers."""

SECONDS_PER_DAY = 86400.0


def compute_listed_days(created_at_ts: float, now: float) -> float:
    """Return the number of days between ``created_at_ts`` and ``now``."""
    return (now - created_at_ts) / SECONDS_PER_DAY


def format_listed_age(days: float | None) -> str:
    """Format a day count as a human-readable listing age."""
    if days is None:
        return ""
    if days < 1 / 24:
        return "just now"
    if days < 1:
        hours = int(days * 24)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if days < 30:
        whole = int(days)
        return f"{whole} day{'s' if whole != 1 else ''} ago"
    if days < 365:
        months = int(days // 30)
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = int(days // 365)
    return f"{years} year{'s' if years != 1 else ''} ago"
