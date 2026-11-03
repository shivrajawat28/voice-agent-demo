"""
Timezone Utility for FertoBot Voice Agent
Ensures all farmer-facing timestamps are strictly presented in Asia/Kolkata (IST, UTC+05:30)
using a 12-hour clock with AM/PM indicators, while preserving internal UTC storage.
"""
from datetime import datetime, timezone, timedelta
from typing import Union, Optional
import zoneinfo

try:
    IST_ZONE = zoneinfo.ZoneInfo("Asia/Kolkata")
except Exception:
    # Fallback to fixed offset +05:30 if zoneinfo database is not present
    IST_ZONE = timezone(timedelta(hours=5, minutes=30), name="IST")

UTC_ZONE = timezone.utc


def to_ist(dt_or_iso: Union[datetime, str, int, float, None]) -> datetime:
    """
    Converts any datetime, ISO-8601 string, or epoch timestamp to an aware Asia/Kolkata datetime.
    Handles date boundaries across UTC midnight accurately.
    """
    if dt_or_iso is None:
        return datetime.now(IST_ZONE)

    if isinstance(dt_or_iso, (int, float)):
        return datetime.fromtimestamp(dt_or_iso, tz=UTC_ZONE).astimezone(IST_ZONE)

    if isinstance(dt_or_iso, str):
        cleaned = dt_or_iso.strip()
        if not cleaned:
            return datetime.now(IST_ZONE)
        try:
            # Handle ISO formats like '2026-11-03T00:00:00Z' or '2026-11-03 00:00:00'
            cleaned = cleaned.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
        except Exception:
            # Fallback for common space-separated formats
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(cleaned, fmt)
                    break
                except ValueError:
                    dt = datetime.now(UTC_ZONE)

        if dt.tzinfo is None:
            # Assume naive timestamps from sensors/logs are in UTC
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(IST_ZONE)

    if isinstance(dt_or_iso, datetime):
        if dt_or_iso.tzinfo is None:
            dt_or_iso = dt_or_iso.replace(tzinfo=UTC_ZONE)
        return dt_or_iso.astimezone(IST_ZONE)

    return datetime.now(IST_ZONE)


def format_to_ist(
    dt_or_iso: Union[datetime, str, int, float, None],
    include_date: bool = True,
    include_seconds: bool = False,
    language: str = "en",
) -> str:
    """
    Formats a timestamp to a 12-hour IST string with AM/PM.
    Examples:
    - '2026-11-03 00:00 UTC' -> '03 Nov 2026, 05:30 AM IST'
    - '2026-11-03 06:30 UTC' -> '03 Nov 2026, 12:00 PM IST'
    - '2026-11-03 13:00 UTC' -> '03 Nov 2026, 06:30 PM IST'
    """
    ist_dt = to_ist(dt_or_iso)

    time_fmt = "%I:%M:%S %p IST" if include_seconds else "%I:%M %p IST"
    if include_date:
        full_fmt = f"%d %b %Y, {time_fmt}"
    else:
        full_fmt = time_fmt

    formatted = ist_dt.strftime(full_fmt)

    # In Hindi, also provide natural readable terms if requested
    if language.lower().startswith("hi"):
        # We preserve standard '03 Nov 2026, 05:30 AM IST' for technical clarity,
        # but replace English month names with readable Devanagari when needed
        month_map = {
            "Jan": "जनवरी", "Feb": "फ़रवरी", "Mar": "मार्च", "Apr": "अप्रैल",
            "May": "मई", "Jun": "जून", "Jul": "जुलाई", "Aug": "अगस्त",
            "Sep": "सितंबर", "Oct": "अक्टूबर", "Nov": "नवंबर", "Dec": "दिसंबर",
        }
        for en_m, hi_m in month_map.items():
            if en_m in formatted:
                formatted = formatted.replace(en_m, hi_m)
                break

    return formatted


def get_current_ist() -> datetime:
    """Returns current aware datetime in Asia/Kolkata timezone."""
    return datetime.now(IST_ZONE)


def get_tomorrow_ist() -> datetime:
    """Returns tomorrow's date at current time in Asia/Kolkata timezone."""
    return datetime.now(IST_ZONE) + timedelta(days=1)
