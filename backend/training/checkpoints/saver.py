# training/checkpoints/saver.py
from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.checkpoint_saver")


def save_checkpoint(
    model: Any,
    optimizer: Any,
    scheduler: Any,
    output_dir: str,
    step: int,
    epoch: int,
    metrics: dict[str, Any] | None = None,
    keep_last_n: int = 3,
) -> str:
    try:
        import torch
    except ImportError as exc:
        raise ImportError("torch not installed; run: pip install -r requirements-worker.txt") from exc

    checkpoint_dir = Path(output_dir) / f"checkpoint-{step}"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    if hasattr(model, "save_pretrained"):
        model.save_pretrained(str(checkpoint_dir))
    else:
        torch.save(model.state_dict(), checkpoint_dir / "model.pt")

    torch.save(optimizer.state_dict(), checkpoint_dir / "optimizer.pt")
    if scheduler is not None:
        torch.save(scheduler.state_dict(), checkpoint_dir / "scheduler.pt")

    metadata = {
        "step": step,
        "epoch": epoch,
        "metrics": metrics or {},
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint_id": uuid.uuid4().hex,
    }
    (checkpoint_dir / "trainer_state.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    if keep_last_n > 0:
        _prune_old_checkpoints(Path(output_dir), keep_last_n)

    logger.info("checkpoint_saved", path=str(checkpoint_dir), step=step)
    return str(checkpoint_dir)


def _prune_old_checkpoints(output_dir: Path, keep_last_n: int) -> None:
    checkpoints = sorted(
        [p for p in output_dir.glob("checkpoint-*") if p.is_dir()],
        key=lambda p: int(p.name.split("-")[-1]),
    )
    for old_checkpoint in checkpoints[:-keep_last_n]:
        shutil.rmtree(old_checkpoint, ignore_errors=True)
        logger.debug("checkpoint_pruned", path=str(old_checkpoint))


def save_best_checkpoint_marker(output_dir: str, checkpoint_path: str, metric_value: float, metric_name: str = "eval_loss") -> None:
    marker_path = Path(output_dir) / "best_checkpoint.json"
    marker_path.write_text(
        json.dumps({"checkpoint_path": checkpoint_path, "metric_name": metric_name, "metric_value": metric_value, "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2),
        encoding="utf-8",
    )
