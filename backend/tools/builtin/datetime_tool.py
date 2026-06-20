# tools/builtin/datetime_tool.py
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, available_timezones

from tools.schemas import ToolParameter, ToolParameterType, ToolSchema

_COMMON_TIMEZONE_ALIASES: dict[str, str] = {
    "usa": "America/New_York", "us": "America/New_York", "united states": "America/New_York",
    "new york": "America/New_York", "nyc": "America/New_York",
    "los angeles": "America/Los_Angeles", "la": "America/Los_Angeles", "california": "America/Los_Angeles",
    "chicago": "America/Chicago", "texas": "America/Chicago",
    "uk": "Europe/London", "united kingdom": "Europe/London", "london": "Europe/London", "england": "Europe/London",
    "india": "Asia/Kolkata", "delhi": "Asia/Kolkata", "mumbai": "Asia/Kolkata", "bangalore": "Asia/Kolkata", "ist": "Asia/Kolkata",
    "japan": "Asia/Tokyo", "tokyo": "Asia/Tokyo",
    "china": "Asia/Shanghai", "beijing": "Asia/Shanghai", "shanghai": "Asia/Shanghai",
    "germany": "Europe/Berlin", "berlin": "Europe/Berlin",
    "france": "Europe/Paris", "paris": "Europe/Paris",
    "australia": "Australia/Sydney", "sydney": "Australia/Sydney",
    "canada": "America/Toronto", "toronto": "America/Toronto",
    "uae": "Asia/Dubai", "dubai": "Asia/Dubai",
    "singapore": "Asia/Singapore",
    "russia": "Europe/Moscow", "moscow": "Europe/Moscow",
    "brazil": "America/Sao_Paulo", "sao paulo": "America/Sao_Paulo",
    "south korea": "Asia/Seoul", "seoul": "Asia/Seoul",
    "utc": "UTC", "gmt": "UTC",
}

GET_CURRENT_TIME_SCHEMA = ToolSchema(
    name="get_current_time",
    description=(
        "Get the exact current date and time for any country, city, or IANA timezone. "
        "Accepts common names like 'USA', 'India', 'Tokyo', 'UTC', or exact IANA timezone IDs like 'America/New_York'. "
        "Returns precise date, time, day of week, UTC offset, and whether daylight saving time is active."
    ),
    parameters=[
        ToolParameter(
            name="location",
            type=ToolParameterType.STRING,
            description="Country, city, or IANA timezone name (e.g. 'USA', 'India', 'Asia/Kolkata', 'UTC'). Defaults to UTC if omitted.",
            required=False,
            default="UTC",
        ),
    ],
    returns="object with exact date, time, timezone, utc_offset, is_dst",
    category="datetime",
)


def _resolve_timezone(location: str) -> ZoneInfo:
    normalized = location.strip().lower()

    if normalized in _COMMON_TIMEZONE_ALIASES:
        return ZoneInfo(_COMMON_TIMEZONE_ALIASES[normalized])

    if location in available_timezones():
        return ZoneInfo(location)

    for tz_name in available_timezones():
        if normalized in tz_name.lower().replace("_", " "):
            return ZoneInfo(tz_name)

    raise ValueError(f"Could not resolve timezone for location: '{location}'")


async def get_current_time_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    location = arguments.get("location", "UTC")
    tz = _resolve_timezone(location)
    now = datetime.now(tz)

    utc_offset = now.utcoffset()
    offset_hours = utc_offset.total_seconds() / 3600 if utc_offset else 0.0

    return {
        "location": location,
        "timezone": str(tz),
        "iso_datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "time_12h": now.strftime("%I:%M:%S %p"),
        "day_of_week": now.strftime("%A"),
        "utc_offset": f"{'+' if offset_hours >= 0 else ''}{offset_hours:g}:00",
        "is_dst": bool(now.dst()) if now.dst() is not None else False,
        "timestamp_unix": int(now.timestamp()),
    }


COMPARE_TIMEZONES_SCHEMA = ToolSchema(
    name="compare_timezones",
    description="Compare the current time across multiple locations/countries at once (e.g. for scheduling meetings across timezones).",
    parameters=[
        ToolParameter(name="locations", type=ToolParameterType.ARRAY, description="List of countries/cities/timezones to compare", required=True, items={"type": "string"}),
    ],
    returns="array of {location, time, date, utc_offset}",
    category="datetime",
)


async def compare_timezones_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    locations = arguments["locations"]
    results = []
    for location in locations:
        try:
            result = await get_current_time_handler({"location": location})
            results.append(result)
        except ValueError as exc:
            results.append({"location": location, "error": str(exc)})
    return {"comparisons": results, "compared_at": datetime.utcnow().isoformat()}
