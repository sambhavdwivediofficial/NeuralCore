# training/exporter.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.exporter")


def export_for_inference(model_path: str, output_path: str, dtype: str = "bfloat16") -> str:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise ImportError("transformers/torch not installed; run: pip install -r requirements-worker.txt") from exc

    dtype_map = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}
    target_dtype = dtype_map.get(dtype, torch.bfloat16)

    model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=target_dtype)
    tokenizer = AutoTokenizer.from_pretrained(model_path)

    model.save_pretrained(output_path, safe_serialization=True)
    tokenizer.save_pretrained(output_path)

    logger.info("model_exported_for_inference", output=output_path, dtype=dtype)
    return output_path


def export_to_onnx(model_path: str, output_path: str, opset_version: int = 17) -> str:
    try:
        from optimum.onnxruntime import ORTModelForCausalLM
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise ImportError("optimum[onnxruntime] not installed; run: pip install optimum[onnxruntime]") from exc

    model = ORTModelForCausalLM.from_pretrained(model_path, export=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path)

    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)

    logger.info("model_exported_onnx", output=output_path)
    return output_path


def compute_model_size_on_disk(model_path: str) -> dict[str, Any]:
    path = Path(model_path)
    total_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return {
        "model_path": model_path,
        "size_bytes": total_bytes,
        "size_gb": round(total_bytes / (1024 ** 3), 3),
        "file_count": sum(1 for f in path.rglob("*") if f.is_file()),
    }
