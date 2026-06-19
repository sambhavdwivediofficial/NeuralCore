# finetuning/lora/adapters.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.finetuning.adapters")


@dataclass(slots=True)
class LoRAAdapterInfo:
    id: str
    name: str
    base_model: str
    path: str
    rank: int
    alpha: int
    target_modules: list[str]
    training_dataset_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "base_model": self.base_model, "path": self.path,
            "rank": self.rank, "alpha": self.alpha, "target_modules": self.target_modules,
            "training_dataset_id": self.training_dataset_id, "created_at": self.created_at,
            "metrics": self.metrics, "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoRAAdapterInfo":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AdapterManager:
    def __init__(self, storage_dir: str = "/data/lora_adapters") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.storage_dir / "registry.json"

    def _load_registry(self) -> dict[str, dict[str, Any]]:
        if not self._registry_path.exists():
            return {}
        return json.loads(self._registry_path.read_text(encoding="utf-8"))

    def _save_registry(self, registry: dict[str, dict[str, Any]]) -> None:
        self._registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    def register(self, adapter: LoRAAdapterInfo) -> None:
        registry = self._load_registry()
        registry[adapter.id] = adapter.to_dict()
        self._save_registry(registry)
        logger.info("lora_adapter_registered", adapter_id=adapter.id, name=adapter.name)

    def get(self, adapter_id: str) -> LoRAAdapterInfo | None:
        registry = self._load_registry()
        data = registry.get(adapter_id)
        return LoRAAdapterInfo.from_dict(data) if data else None

    def list_adapters(self, base_model: str | None = None) -> list[LoRAAdapterInfo]:
        registry = self._load_registry()
        adapters = [LoRAAdapterInfo.from_dict(data) for data in registry.values()]
        if base_model:
            adapters = [a for a in adapters if a.base_model == base_model]
        return adapters

    def delete(self, adapter_id: str) -> bool:
        registry = self._load_registry()
        if adapter_id not in registry:
            return False
        adapter_path = Path(registry[adapter_id]["path"])
        if adapter_path.exists():
            import shutil
            shutil.rmtree(adapter_path, ignore_errors=True)
        del registry[adapter_id]
        self._save_registry(registry)
        return True

    def get_adapter_path(self, adapter_id: str) -> str | None:
        adapter = self.get(adapter_id)
        return adapter.path if adapter else None


def merge_adapter_into_base_model(base_model_path: str, adapter_path: str, output_path: str) -> str:
    try:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise ImportError("transformers/peft not installed; run: pip install -r requirements-worker.txt") from exc

    base_model = AutoModelForCausalLM.from_pretrained(base_model_path)
    model = PeftModel.from_pretrained(base_model, adapter_path)
    merged_model = model.merge_and_unload()

    tokenizer = AutoTokenizer.from_pretrained(base_model_path)
    merged_model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)

    logger.info("lora_adapter_merged", base_model=base_model_path, adapter=adapter_path, output=output_path)
    return output_path
