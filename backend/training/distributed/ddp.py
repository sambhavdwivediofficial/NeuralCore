# training/distributed/ddp.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.distributed.ddp")


@dataclass(slots=True)
class DDPConfig:
    backend: str = "nccl"
    find_unused_parameters: bool = False
    gradient_as_bucket_view: bool = True
    static_graph: bool = False


def is_distributed_environment() -> bool:
    return "WORLD_SIZE" in os.environ and int(os.environ.get("WORLD_SIZE", "1")) > 1


def get_distributed_info() -> dict[str, int]:
    return {
        "world_size": int(os.environ.get("WORLD_SIZE", "1")),
        "rank": int(os.environ.get("RANK", "0")),
        "local_rank": int(os.environ.get("LOCAL_RANK", "0")),
    }


def init_ddp_process_group(config: DDPConfig) -> None:
    try:
        import torch.distributed as dist
    except ImportError as exc:
        raise ImportError("torch not installed; run: pip install -r requirements-worker.txt") from exc

    if not dist.is_initialized():
        dist.init_process_group(backend=config.backend)
        logger.info("ddp_process_group_initialized", backend=config.backend, **get_distributed_info())


def wrap_model_ddp(model: Any, config: DDPConfig) -> Any:
    try:
        import torch
        from torch.nn.parallel import DistributedDataParallel as DDP
    except ImportError as exc:
        raise ImportError("torch not installed; run: pip install -r requirements-worker.txt") from exc

    info = get_distributed_info()
    device = torch.device(f"cuda:{info['local_rank']}")
    model = model.to(device)

    return DDP(
        model, device_ids=[info["local_rank"]],
        find_unused_parameters=config.find_unused_parameters,
        gradient_as_bucket_view=config.gradient_as_bucket_view,
        static_graph=config.static_graph,
    )


def cleanup_ddp() -> None:
    try:
        import torch.distributed as dist
        if dist.is_initialized():
            dist.destroy_process_group()
    except ImportError:
        pass
