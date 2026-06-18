# analytics/metrics.py
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.analytics.metrics")


class TimeRange(str, Enum):
    HOUR_24 = "24h"
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"


def range_to_timedelta(range_str: str) -> timedelta:
    mapping: dict[str, timedelta] = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    return mapping.get(range_str, timedelta(days=7))


def range_to_interval(range_str: str) -> str:
    mapping = {"24h": "1 hour", "7d": "1 day", "30d": "1 day", "90d": "7 days"}
    return mapping.get(range_str, "1 day")


def range_to_bucket_format(range_str: str) -> str:
    mapping = {"24h": "%Y-%m-%dT%H:00:00Z", "7d": "%Y-%m-%d", "30d": "%Y-%m-%d", "90d": "%Y-%m-%d"}
    return mapping.get(range_str, "%Y-%m-%d")


@dataclass(slots=True, frozen=True)
class MetricPoint:
    timestamp: str
    value: float
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"timestamp": self.timestamp, "value": self.value}
        if self.label:
            result["label"] = self.label
        return result


@dataclass(slots=True)
class MetricSeries:
    name: str
    points: list[MetricPoint] = field(default_factory=list)
    unit: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def total(self) -> float:
        return sum(p.value for p in self.points)

    def average(self) -> float:
        if not self.points:
            return 0.0
        return self.total() / len(self.points)

    def maximum(self) -> float:
        return max((p.value for p in self.points), default=0.0)

    def minimum(self) -> float:
        return min((p.value for p in self.points), default=0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "points": [p.to_dict() for p in self.points],
            "unit": self.unit,
            "total": self.total(),
            "average": self.average(),
            "max": self.maximum(),
            "min": self.minimum(),
            "metadata": self.metadata,
        }


def generate_empty_time_series(
    range_str: str,
    name: str,
    unit: str = "",
) -> MetricSeries:
    delta = range_to_timedelta(range_str)
    fmt = range_to_bucket_format(range_str)
    now = datetime.now(timezone.utc)
    start = now - delta
    points: list[MetricPoint] = []

    if range_str == "24h":
        current = start.replace(minute=0, second=0, microsecond=0)
        while current <= now:
            points.append(MetricPoint(timestamp=current.strftime(fmt), value=0.0))
            current += timedelta(hours=1)
    elif range_str == "90d":
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)
        while current <= now:
            points.append(MetricPoint(timestamp=current.strftime(fmt), value=0.0))
            current += timedelta(weeks=1)
    else:
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)
        while current <= now:
            points.append(MetricPoint(timestamp=current.strftime(fmt), value=0.0))
            current += timedelta(days=1)

    return MetricSeries(name=name, points=points, unit=unit)


async def fetch_metric_series_from_db(
    db: Any,
    table: str,
    value_column: str,
    range_str: str,
    name: str,
    unit: str = "",
    filters: dict[str, Any] | None = None,
    aggregate: str = "SUM",
) -> MetricSeries:
    from database.connection import get_engine
    from sqlalchemy import text

    delta = range_to_timedelta(range_str)
    interval = range_to_interval(range_str)
    since = datetime.now(timezone.utc) - delta
    series = generate_empty_time_series(range_str, name, unit)

    engine = get_engine()
    try:
        where_clauses = ["created_at >= :since"]
        params: dict[str, Any] = {"since": since}
        if filters:
            for key, value in filters.items():
                where_clauses.append(f"{key} = :{key}")
                params[key] = value

        query = f"""
            SELECT
                date_trunc(:interval, created_at) AS bucket,
                {aggregate}({value_column}) AS val
            FROM {table}
            WHERE {' AND '.join(where_clauses)}
            GROUP BY bucket
            ORDER BY bucket
        """
        params["interval"] = interval.split()[1] if " " in interval else interval

        async with engine.connect() as conn:
            result = await conn.execute(text(query), params)
            rows = result.mappings().all()

        bucket_map: dict[str, float] = {row["bucket"].strftime("%Y-%m-%dT%H:%M:%SZ" if range_str == "24h" else "%Y-%m-%d"): float(row["val"] or 0) for row in rows}
        for point in series.points:
            if point.timestamp in bucket_map:
                series.points[series.points.index(point)] = MetricPoint(
                    timestamp=point.timestamp, value=bucket_map[point.timestamp]
                )
    except Exception as exc:
        logger.warning("metric_series_db_fetch_failed", table=table, error=str(exc))

    return series
