# training/distributed/fsdp.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.distributed.fsdp")


@dataclass(slots=True)
class FSDPConfig:
    sharding_strategy: str = "FULL_SHARD"
    mixed_precision: bool = True
    cpu_offload: bool = False
    auto_wrap_min_params: int = 100_000_000
    backward_prefetch: str = "BACKWARD_PRE"
    activation_checkpointing: bool = True


def build_auto_wrap_policy(config: FSDPConfig, transformer_layer_cls: Any = None) -> Any:
    try:
        from torch.distributed.fsdp.wrap import size_based_auto_wrap_policy, transformer_auto_wrap_policy
    except ImportError as exc:
        raise ImportError("torch not installed; run: pip install -r requirements-worker.txt") from exc

    if transformer_layer_cls is not None:
        import functools
        return functools.partial(transformer_auto_wrap_policy, transformer_layer_cls={transformer_layer_cls})

    import functools
    return functools.partial(size_based_auto_wrap_policy, min_num_params=config.auto_wrap_min_params)


def wrap_model_fsdp(model: Any, config: FSDPConfig, transformer_layer_cls: Any = None) -> Any:
    try:
        import torch
        from torch.distributed.fsdp import (
            BackwardPrefetch,
            CPUOffload,
            FullyShardedDataParallel as FSDP,
            MixedPrecision,
            ShardingStrategy,
        )
    except ImportError as exc:
        raise ImportError("torch not installed; run: pip install -r requirements-worker.txt") from exc

    sharding_map = {
        "FULL_SHARD": ShardingStrategy.FULL_SHARD,
        "SHARD_GRAD_OP": ShardingStrategy.SHARD_GRAD_OP,
        "NO_SHARD": ShardingStrategy.NO_SHARD,
        "HYBRID_SHARD": ShardingStrategy.HYBRID_SHARD,
    }

    mixed_precision_policy = None
    if config.mixed_precision:
        mixed_precision_policy = MixedPrecision(
            param_dtype=torch.bfloat16, reduce_dtype=torch.bfloat16, buffer_dtype=torch.bfloat16,
        )

    auto_wrap_policy = build_auto_wrap_policy(config, transformer_layer_cls)
    backward_prefetch = getattr(BackwardPrefetch, config.backward_prefetch, BackwardPrefetch.BACKWARD_PRE)

    wrapped = FSDP(
        model,
        sharding_strategy=sharding_map.get(config.sharding_strategy, ShardingStrategy.FULL_SHARD),
        mixed_precision=mixed_precision_policy,
        cpu_offload=CPUOffload(offload_params=True) if config.cpu_offload else None,
        auto_wrap_policy=auto_wrap_policy,
        backward_prefetch=backward_prefetch,
    )

    logger.info("fsdp_model_wrapped", sharding_strategy=config.sharding_strategy, cpu_offload=config.cpu_offload)
    return wrapped
