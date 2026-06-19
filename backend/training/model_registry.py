# training/model_registry.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.model_registry")


@dataclass(slots=True)
class RegisteredModel:
    id: str
    name: str
    version: str
    model_path: str
    base_model: str | None
    training_job_id: str | None
    metrics: dict[str, Any] = field(default_factory=dict)
    stage: str = "staging"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "version": self.version, "model_path": self.model_path,
            "base_model": self.base_model, "training_job_id": self.training_job_id, "metrics": self.metrics,
            "stage": self.stage, "created_at": self.created_at, "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegisteredModel":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ModelRegistry:
    def __init__(self, storage_dir: str = "/data/model_registry") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.storage_dir / "registry.json"

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._registry_path.exists():
            return {}
        return json.loads(self._registry_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self._registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def register_model(
        self, name: str, model_path: str, base_model: str | None = None, training_job_id: str | None = None, metrics: dict[str, Any] | None = None,
    ) -> RegisteredModel:
        existing_versions = [m["version"] for m in self._load().values() if m["name"] == name]
        next_version = f"v{len(existing_versions) + 1}"

        model = RegisteredModel(
            id=uuid.uuid4().hex, name=name, version=next_version, model_path=model_path,
            base_model=base_model, training_job_id=training_job_id, metrics=metrics or {},
        )
        registry = self._load()
        registry[model.id] = model.to_dict()
        self._save(registry)
        logger.info("model_registered", model_id=model.id, name=name, version=next_version)
        return model

    def get_model(self, model_id: str) -> RegisteredModel | None:
        data = self._load().get(model_id)
        return RegisteredModel.from_dict(data) if data else None

    def promote_to_production(self, model_id: str) -> RegisteredModel | None:
        registry = self._load()
        if model_id not in registry:
            return None

        target = RegisteredModel.from_dict(registry[model_id])
        for other_id, other_data in registry.items():
            if other_data["name"] == target.name and other_data["stage"] == "production":
                registry[other_id]["stage"] = "archived"

        registry[model_id]["stage"] = "production"
        self._save(registry)
        logger.info("model_promoted_to_production", model_id=model_id, name=target.name)
        return self.get_model(model_id)

    def get_production_model(self, name: str) -> RegisteredModel | None:
        registry = self._load()
        for data in registry.values():
            if data["name"] == name and data["stage"] == "production":
                return RegisteredModel.from_dict(data)
        return None

    def list_models(self, name: str | None = None, stage: str | None = None) -> list[RegisteredModel]:
        registry = self._load()
        models = [RegisteredModel.from_dict(data) for data in registry.values()]
        if name:
            models = [m for m in models if m.name == name]
        if stage:
            models = [m for m in models if m.stage == stage]
        return sorted(models, key=lambda m: m.created_at, reverse=True)
