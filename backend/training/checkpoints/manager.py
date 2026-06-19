# training/checkpoints/manager.py
from __future__ import annotations

from typing import Any

from monitoring.logging import get_logger
from training.checkpoints.loader import find_best_checkpoint, find_latest_checkpoint, list_all_checkpoints, load_checkpoint
from training.checkpoints.saver import save_best_checkpoint_marker, save_checkpoint

logger = get_logger("neuralcore.training.checkpoint_manager")


class CheckpointManager:
    def __init__(self, output_dir: str, keep_last_n: int = 3, metric_name: str = "eval_loss", lower_is_better: bool = True) -> None:
        self.output_dir = output_dir
        self.keep_last_n = keep_last_n
        self.metric_name = metric_name
        self.lower_is_better = lower_is_better
        self._best_metric: float | None = None

    def save(self, model: Any, optimizer: Any, scheduler: Any, step: int, epoch: int, metrics: dict[str, Any] | None = None) -> str:
        checkpoint_path = save_checkpoint(model, optimizer, scheduler, self.output_dir, step, epoch, metrics, self.keep_last_n)

        if metrics and self.metric_name in metrics:
            current_value = metrics[self.metric_name]
            is_better = (
                self._best_metric is None
                or (self.lower_is_better and current_value < self._best_metric)
                or (not self.lower_is_better and current_value > self._best_metric)
            )
            if is_better:
                self._best_metric = current_value
                save_best_checkpoint_marker(self.output_dir, checkpoint_path, current_value, self.metric_name)
                logger.info("new_best_checkpoint", metric=self.metric_name, value=current_value)

        return checkpoint_path

    def resume_latest(self, model: Any, optimizer: Any = None, scheduler: Any = None) -> dict[str, Any] | None:
        latest = find_latest_checkpoint(self.output_dir)
        if latest is None:
            return None
        return load_checkpoint(latest, model, optimizer, scheduler)

    def load_best(self, model: Any) -> dict[str, Any] | None:
        best = find_best_checkpoint(self.output_dir)
        if best is None:
            return None
        return load_checkpoint(best, model)

    def list_checkpoints(self) -> list[dict[str, Any]]:
        return list_all_checkpoints(self.output_dir)
