# training/distributed/launcher.py
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.distributed.launcher")


@dataclass(slots=True)
class LaunchConfig:
    script_path: str
    num_gpus: int = 1
    num_nodes: int = 1
    node_rank: int = 0
    master_addr: str = "localhost"
    master_port: int = 29500
    distributed_backend: str = "ddp"
    extra_args: list[str] = field(default_factory=list)


def build_torchrun_command(config: LaunchConfig) -> list[str]:
    nproc = config.num_gpus
    cmd = [
        "torchrun",
        f"--nproc_per_node={nproc}",
        f"--nnodes={config.num_nodes}",
        f"--node_rank={config.node_rank}",
        f"--master_addr={config.master_addr}",
        f"--master_port={config.master_port}",
        config.script_path,
        *config.extra_args,
    ]
    return cmd


def build_deepspeed_command(config: LaunchConfig, hostfile: str | None = None) -> list[str]:
    cmd = ["deepspeed", f"--num_gpus={config.num_gpus}"]
    if hostfile:
        cmd.append(f"--hostfile={hostfile}")
    cmd.extend([config.script_path, *config.extra_args])
    return cmd


def detect_available_gpus() -> int:
    try:
        import torch
        return torch.cuda.device_count() if torch.cuda.is_available() else 0
    except ImportError:
        return 0


async def launch_training_job(config: LaunchConfig) -> dict[str, Any]:
    import asyncio

    if config.distributed_backend == "deepspeed":
        cmd = build_deepspeed_command(config)
    else:
        cmd = build_torchrun_command(config)

    logger.info("launching_training_job", command=" ".join(cmd))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return {"pid": process.pid, "command": cmd, "status": "launched"}


def get_optimal_launch_config(script_path: str, model_size_billions: float) -> LaunchConfig:
    available_gpus = detect_available_gpus()
    backend = "deepspeed" if model_size_billions > 13 and available_gpus > 1 else "ddp"
    return LaunchConfig(script_path=script_path, num_gpus=max(available_gpus, 1), distributed_backend=backend)
