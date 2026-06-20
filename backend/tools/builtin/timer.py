# tools/builtin/timer.py
from __future__ import annotations

import asyncio
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from tools.schemas import ToolParameter, ToolParameterType, ToolSchema

logger = get_logger("neuralcore.tools.timer")

_DURATION_PATTERN = re.compile(r"(\d+)\s*(h|hr|hour|hours|m|min|minute|minutes|s|sec|second|seconds)", re.IGNORECASE)
_UNIT_TO_SECONDS = {
    "h": 3600, "hr": 3600, "hour": 3600, "hours": 3600,
    "m": 60, "min": 60, "minute": 60, "minutes": 60,
    "s": 1, "sec": 1, "second": 1, "seconds": 1,
}

_MAX_TIMER_SECONDS = 24 * 3600


@dataclass(slots=True)
class TimerState:
    id: str
    duration_seconds: int
    label: str
    started_at: float
    expires_at: float
    status: str = "running"

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.expires_at - time.time())

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "duration_seconds": self.duration_seconds,
            "remaining_seconds": round(self.remaining_seconds, 1),
            "status": "completed" if self.is_expired and self.status == "running" else self.status,
            "started_at": self.started_at,
            "expires_at": self.expires_at,
        }


_active_timers: dict[str, TimerState] = {}


def parse_duration_to_seconds(duration_text: str) -> int:
    matches = _DURATION_PATTERN.findall(duration_text)
    if not matches:
        try:
            return int(float(duration_text))
        except ValueError:
            raise ValueError(f"Could not parse duration: '{duration_text}'. Use formats like '10 minutes', '1h 30m', '90s'.")

    total_seconds = 0
    for value, unit in matches:
        total_seconds += int(value) * _UNIT_TO_SECONDS.get(unit.lower(), 1)
    return total_seconds


START_TIMER_SCHEMA = ToolSchema(
    name="start_timer",
    description=(
        "Start a precise countdown timer for a specified duration. Accepts natural language durations like "
        "'10 minutes', '1 hour 30 minutes', '90 seconds', or plain numbers (interpreted as seconds). "
        "Returns a timer_id that can be used to check status later."
    ),
    parameters=[
        ToolParameter(name="duration", type=ToolParameterType.STRING, description="Duration like '10 minutes', '1h30m', '45s', or a number of seconds", required=True),
        ToolParameter(name="label", type=ToolParameterType.STRING, description="Optional label for this timer", required=False, default="Timer"),
    ],
    returns="object with timer_id, expires_at, duration_seconds",
    category="utility",
)


async def start_timer_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime, timezone

    duration_seconds = parse_duration_to_seconds(arguments["duration"])
    if duration_seconds <= 0:
        raise ValueError("Timer duration must be greater than 0 seconds")
    if duration_seconds > _MAX_TIMER_SECONDS:
        raise ValueError(f"Timer duration cannot exceed 24 hours ({_MAX_TIMER_SECONDS} seconds)")

    timer_id = uuid.uuid4().hex[:12]
    now = time.time()
    timer = TimerState(
        id=timer_id,
        duration_seconds=duration_seconds,
        label=arguments.get("label", "Timer"),
        started_at=now,
        expires_at=now + duration_seconds,
    )
    _active_timers[timer_id] = timer

    expires_at_dt = datetime.fromtimestamp(timer.expires_at, tz=timezone.utc)

    logger.info("timer_started", timer_id=timer_id, duration_seconds=duration_seconds, label=timer.label)

    return {
        "timer_id": timer_id,
        "label": timer.label,
        "duration_seconds": duration_seconds,
        "started_at_iso": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "expires_at_iso": expires_at_dt.isoformat(),
        "status": "running",
    }


CHECK_TIMER_SCHEMA = ToolSchema(
    name="check_timer",
    description="Check the remaining time on a previously started timer using its timer_id.",
    parameters=[
        ToolParameter(name="timer_id", type=ToolParameterType.STRING, description="The timer_id returned by start_timer", required=True),
    ],
    returns="object with remaining_seconds, status",
    category="utility",
)


async def check_timer_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    timer_id = arguments["timer_id"]
    timer = _active_timers.get(timer_id)
    if timer is None:
        raise ValueError(f"No timer found with id '{timer_id}'")
    return timer.to_dict()


WAIT_FOR_TIMER_SCHEMA = ToolSchema(
    name="wait_for_timer",
    description="Block and wait until a started timer completes, then return. Useful when the agent needs to actually pause execution for the duration.",
    parameters=[
        ToolParameter(name="timer_id", type=ToolParameterType.STRING, description="The timer_id returned by start_timer", required=True),
    ],
    returns="object confirming completion",
    category="utility",
)


async def wait_for_timer_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    timer_id = arguments["timer_id"]
    timer = _active_timers.get(timer_id)
    if timer is None:
        raise ValueError(f"No timer found with id '{timer_id}'")

    remaining = timer.remaining_seconds
    if remaining > 0:
        await asyncio.sleep(min(remaining, 110.0))

    timer.status = "completed"
    logger.info("timer_completed", timer_id=timer_id, label=timer.label)
    return {"timer_id": timer_id, "label": timer.label, "status": "completed"}


CANCEL_TIMER_SCHEMA = ToolSchema(
    name="cancel_timer",
    description="Cancel a running timer before it completes.",
    parameters=[
        ToolParameter(name="timer_id", type=ToolParameterType.STRING, description="The timer_id to cancel", required=True),
    ],
    returns="confirmation",
    category="utility",
)


async def cancel_timer_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    timer_id = arguments["timer_id"]
    timer = _active_timers.pop(timer_id, None)
    if timer is None:
        raise ValueError(f"No timer found with id '{timer_id}'")
    return {"timer_id": timer_id, "status": "cancelled"}
