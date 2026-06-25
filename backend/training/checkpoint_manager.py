# backend/training/checkpoint_manager.py
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from settings import get_settings


class CheckpointManager:
    def __init__(
        self,
        experiment_id: str,
        base_dir: Optional[str] = None,
        max_checkpoints: int = 5,
        save_optimizer_state: bool = True,
    ) -> None:
        self.experiment_id = experiment_id
        self.max_checkpoints = max_checkpoints
        self.save_optimizer_state = save_optimizer_state
        settings = get_settings()
        self.base_dir = Path(base_dir or "/data/checkpoints") / experiment_id
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.base_dir / "metadata.json"
        self._metadata: dict[str, Any] = self._load_metadata()

    def _load_metadata(self) -> dict[str, Any]:
        if self.metadata_path.exists():
            with open(self.metadata_path, "r") as f:
                return json.load(f)
        return {
            "experiment_id": self.experiment_id,
            "checkpoints": [],
            "best_checkpoint": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _save_metadata(self) -> None:
        with open(self.metadata_path, "w") as f:
            json.dump(self._metadata, f, indent=2)

    def save(
        self,
        step: int,
        epoch: int,
        model_state: dict[str, Any],
        optimizer_state: Optional[dict[str, Any]] = None,
        metrics: Optional[dict[str, float]] = None,
        is_best: bool = False,
        tags: Optional[list[str]] = None,
    ) -> Path:
        checkpoint_name = f"checkpoint_step_{step:08d}_epoch_{epoch:04d}"
        checkpoint_dir = self.base_dir / checkpoint_name
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        model_path = checkpoint_dir / "model_state.json"
        with open(model_path, "w") as f:
            json.dump(model_state, f)

        if self.save_optimizer_state and optimizer_state is not None:
            optimizer_path = checkpoint_dir / "optimizer_state.json"
            with open(optimizer_path, "w") as f:
                json.dump(optimizer_state, f)

        checkpoint_meta = {
            "name": checkpoint_name,
            "step": step,
            "epoch": epoch,
            "path": str(checkpoint_dir),
            "metrics": metrics or {},
            "tags": tags or [],
            "is_best": is_best,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        meta_path = checkpoint_dir / "checkpoint_meta.json"
        with open(meta_path, "w") as f:
            json.dump(checkpoint_meta, f, indent=2)

        self._metadata["checkpoints"].append(checkpoint_meta)

        if is_best:
            best_link = self.base_dir / "best"
            if best_link.exists() or best_link.is_symlink():
                best_link.unlink()
            best_link.symlink_to(checkpoint_dir.name)
            self._metadata["best_checkpoint"] = checkpoint_name

        self._rotate_checkpoints()
        self._save_metadata()
        return checkpoint_dir

    def _rotate_checkpoints(self) -> None:
        non_best = [
            c for c in self._metadata["checkpoints"]
            if not c.get("is_best") and "keep" not in c.get("tags", [])
        ]
        if len(non_best) <= self.max_checkpoints:
            return

        to_delete = non_best[: len(non_best) - self.max_checkpoints]
        for ckpt in to_delete:
            ckpt_path = Path(ckpt["path"])
            if ckpt_path.exists():
                shutil.rmtree(ckpt_path)
            self._metadata["checkpoints"] = [
                c for c in self._metadata["checkpoints"]
                if c["name"] != ckpt["name"]
            ]

    def load(self, checkpoint_name: Optional[str] = None) -> dict[str, Any]:
        if checkpoint_name is None:
            if not self._metadata["checkpoints"]:
                raise FileNotFoundError(f"No checkpoints found for experiment {self.experiment_id}")
            checkpoint_name = self._metadata["checkpoints"][-1]["name"]

        checkpoint_dir = self.base_dir / checkpoint_name
        if not checkpoint_dir.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_dir}")

        model_path = checkpoint_dir / "model_state.json"
        with open(model_path, "r") as f:
            model_state = json.load(f)

        optimizer_state = None
        optimizer_path = checkpoint_dir / "optimizer_state.json"
        if optimizer_path.exists():
            with open(optimizer_path, "r") as f:
                optimizer_state = json.load(f)

        meta_path = checkpoint_dir / "checkpoint_meta.json"
        with open(meta_path, "r") as f:
            meta = json.load(f)

        return {
            "model_state": model_state,
            "optimizer_state": optimizer_state,
            "step": meta["step"],
            "epoch": meta["epoch"],
            "metrics": meta.get("metrics", {}),
            "checkpoint_name": checkpoint_name,
        }

    def load_best(self) -> dict[str, Any]:
        if not self._metadata.get("best_checkpoint"):
            raise FileNotFoundError(f"No best checkpoint for experiment {self.experiment_id}")
        return self.load(self._metadata["best_checkpoint"])

    def load_latest(self) -> dict[str, Any]:
        return self.load(None)

    def list_checkpoints(self) -> list[dict[str, Any]]:
        return list(self._metadata["checkpoints"])

    def get_best_checkpoint(self) -> Optional[dict[str, Any]]:
        best_name = self._metadata.get("best_checkpoint")
        if not best_name:
            return None
        for ckpt in self._metadata["checkpoints"]:
            if ckpt["name"] == best_name:
                return ckpt
        return None

    def delete_checkpoint(self, checkpoint_name: str) -> bool:
        checkpoint_dir = self.base_dir / checkpoint_name
        if checkpoint_dir.exists():
            shutil.rmtree(checkpoint_dir)
        self._metadata["checkpoints"] = [
            c for c in self._metadata["checkpoints"]
            if c["name"] != checkpoint_name
        ]
        if self._metadata.get("best_checkpoint") == checkpoint_name:
            self._metadata["best_checkpoint"] = None
        self._save_metadata()
        return True

    def tag_checkpoint(self, checkpoint_name: str, tag: str) -> bool:
        for ckpt in self._metadata["checkpoints"]:
            if ckpt["name"] == checkpoint_name:
                if tag not in ckpt["tags"]:
                    ckpt["tags"].append(tag)
                self._save_metadata()
                return True
        return False

    def export_checkpoint(self, checkpoint_name: str, export_path: str) -> Path:
        checkpoint_dir = self.base_dir / checkpoint_name
        if not checkpoint_dir.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_dir}")
        export_dir = Path(export_path)
        export_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(checkpoint_dir), str(export_dir / checkpoint_name), dirs_exist_ok=True)
        return export_dir / checkpoint_name

    def get_metrics_history(self, metric_name: str) -> list[dict[str, Any]]:
        history = []
        for ckpt in self._metadata["checkpoints"]:
            if metric_name in ckpt.get("metrics", {}):
                history.append({
                    "step": ckpt["step"],
                    "epoch": ckpt["epoch"],
                    "value": ckpt["metrics"][metric_name],
                    "checkpoint_name": ckpt["name"],
                })
        return sorted(history, key=lambda x: x["step"])

    @property
    def experiment_dir(self) -> Path:
        return self.base_dir

    def cleanup(self, keep_best: bool = True, keep_tagged: bool = True) -> int:
        deleted = 0
        to_delete = []
        for ckpt in self._metadata["checkpoints"]:
            if keep_best and ckpt.get("is_best"):
                continue
            if keep_tagged and ckpt.get("tags"):
                continue
            to_delete.append(ckpt["name"])

        for name in to_delete:
            if self.delete_checkpoint(name):
                deleted += 1
        return deleted
