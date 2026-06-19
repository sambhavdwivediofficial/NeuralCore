# training/checkpoints/loader.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.checkpoint_loader")


def load_checkpoint(
    checkpoint_dir: str,
    model: Any,
    optimizer: Any = None,
    scheduler: Any = None,
    map_location: str = "cpu",
) -> dict[str, Any]:
    try:
        import torch
    except ImportError as exc:
        raise ImportError("torch not installed; run: pip install -r requirements-worker.txt") from exc

    path = Path(checkpoint_dir)
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint directory not found: {checkpoint_dir}")

    if hasattr(model, "from_pretrained") and (path / "config.json").exists():
        model = type(model).from_pretrained(str(path))
    elif (path / "model.pt").exists():
        state_dict = torch.load(path / "model.pt", map_location=map_location)
        model.load_state_dict(state_dict)

    if optimizer is not None and (path / "optimizer.pt").exists():
        optimizer.load_state_dict(torch.load(path / "optimizer.pt", map_location=map_location))

    if scheduler is not None and (path / "scheduler.pt").exists():
        scheduler.load_state_dict(torch.load(path / "scheduler.pt", map_location=map_location))

    metadata: dict[str, Any] = {}
    state_path = path / "trainer_state.json"
    if state_path.exists():
        metadata = json.loads(state_path.read_text(encoding="utf-8"))

    logger.info("checkpoint_loaded", path=checkpoint_dir, step=metadata.get("step", 0))
    return metadata


def find_latest_checkpoint(output_dir: str) -> str | None:
    path = Path(output_dir)
    if not path.exists():
        return None
    checkpoints = sorted(
        [p for p in path.glob("checkpoint-*") if p.is_dir()],
        key=lambda p: int(p.name.split("-")[-1]) if p.name.split("-")[-1].isdigit() else -1,
    )
    return str(checkpoints[-1]) if checkpoints else None


def find_best_checkpoint(output_dir: str) -> str | None:
    marker_path = Path(output_dir) / "best_checkpoint.json"
    if not marker_path.exists():
        return None
    data = json.loads(marker_path.read_text(encoding="utf-8"))
    return data.get("checkpoint_path")


def list_all_checkpoints(output_dir: str) -> list[dict[str, Any]]:
    path = Path(output_dir)
    if not path.exists():
        return []
    results: list[dict[str, Any]] = []
    for checkpoint_path in sorted(path.glob("checkpoint-*")):
        if not checkpoint_path.is_dir():
            continue
        state_file = checkpoint_path / "trainer_state.json"
        metadata = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
        results.append({"path": str(checkpoint_path), **metadata})
    return results
