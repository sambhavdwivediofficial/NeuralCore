# finetuning/registry.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.finetuning.registry")


@dataclass(slots=True)
class FineTuneJobRecord:
    id: str
    name: str
    base_model: str
    status: str
    dataset_id: str | None = None
    output_path: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    error: str | None = None
    organization_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "base_model": self.base_model, "status": self.status,
            "dataset_id": self.dataset_id, "output_path": self.output_path, "config": self.config,
            "metrics": self.metrics, "created_at": self.created_at, "completed_at": self.completed_at,
            "error": self.error, "organization_id": self.organization_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FineTuneJobRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class FineTuneRegistry:
    def __init__(self, storage_dir: str = "/data/finetune_jobs") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.storage_dir / "jobs.json"

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._registry_path.exists():
            return {}
        return json.loads(self._registry_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self._registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def create_job(
        self, name: str, base_model: str, dataset_id: str | None = None, config: dict[str, Any] | None = None, organization_id: str | None = None
    ) -> FineTuneJobRecord:
        job = FineTuneJobRecord(
            id=uuid.uuid4().hex, name=name, base_model=base_model, status="pending",
            dataset_id=dataset_id, config=config or {}, organization_id=organization_id,
        )
        registry = self._load()
        registry[job.id] = job.to_dict()
        self._save(registry)
        return job

    def get_job(self, job_id: str) -> FineTuneJobRecord | None:
        registry = self._load()
        data = registry.get(job_id)
        return FineTuneJobRecord.from_dict(data) if data else None

    def update_job(self, job_id: str, **updates: Any) -> FineTuneJobRecord | None:
        registry = self._load()
        if job_id not in registry:
            return None
        registry[job_id].update(updates)
        self._save(registry)
        return FineTuneJobRecord.from_dict(registry[job_id])

    def list_jobs(self, organization_id: str | None = None, status: str | None = None) -> list[FineTuneJobRecord]:
        registry = self._load()
        jobs = [FineTuneJobRecord.from_dict(data) for data in registry.values()]
        if organization_id:
            jobs = [j for j in jobs if j.organization_id == organization_id]
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def delete_job(self, job_id: str) -> bool:
        registry = self._load()
        if job_id not in registry:
            return False
        del registry[job_id]
        self._save(registry)
        return True
