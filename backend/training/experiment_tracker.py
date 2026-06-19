# training/experiment_tracker.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.experiment_tracker")


@dataclass(slots=True)
class ExperimentRun:
    id: str
    name: str
    config: dict[str, Any]
    metrics_log: list[dict[str, Any]] = field(default_factory=list)
    status: str = "running"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "config": self.config,
            "metrics_log": self.metrics_log[-500:], "status": self.status,
            "started_at": self.started_at, "ended_at": self.ended_at, "tags": self.tags,
        }


class ExperimentTracker:
    def __init__(self, storage_dir: str = "/data/experiments") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.storage_dir / f"{run_id}.json"

    def start_run(self, name: str, config: dict[str, Any], tags: list[str] | None = None) -> ExperimentRun:
        run = ExperimentRun(id=uuid.uuid4().hex, name=name, config=config, tags=tags or [])
        self._save(run)
        logger.info("experiment_run_started", run_id=run.id, name=name)
        return run

    def log_metrics(self, run_id: str, step: int, metrics: dict[str, Any]) -> None:
        run = self.get_run(run_id)
        if run is None:
            return
        run.metrics_log.append({"step": step, "timestamp": datetime.now(timezone.utc).isoformat(), **metrics})
        self._save(run)

    def end_run(self, run_id: str, status: str = "completed") -> None:
        run = self.get_run(run_id)
        if run is None:
            return
        run.status = status
        run.ended_at = datetime.now(timezone.utc).isoformat()
        self._save(run)
        logger.info("experiment_run_ended", run_id=run_id, status=status)

    def get_run(self, run_id: str) -> ExperimentRun | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ExperimentRun(**data)

    def list_runs(self, tag: str | None = None) -> list[ExperimentRun]:
        runs: list[ExperimentRun] = []
        for path in self.storage_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            run = ExperimentRun(**data)
            if tag is None or tag in run.tags:
                runs.append(run)
        return sorted(runs, key=lambda r: r.started_at, reverse=True)

    def compare_runs(self, run_ids: list[str], metric_name: str) -> dict[str, Any]:
        comparison: dict[str, Any] = {}
        for run_id in run_ids:
            run = self.get_run(run_id)
            if run is None or not run.metrics_log:
                continue
            values = [m.get(metric_name) for m in run.metrics_log if metric_name in m]
            if values:
                comparison[run_id] = {"name": run.name, "final_value": values[-1], "best_value": min(values), "history_length": len(values)}
        return comparison

    def _save(self, run: ExperimentRun) -> None:
        self._path(run.id).write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
