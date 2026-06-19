# finetuning/exporter.py
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.finetuning.exporter")


def export_to_gguf(model_path: str, output_path: str, quantization: str = "q4_k_m") -> str:
    import subprocess

    try:
        result = subprocess.run(
            ["python", "-m", "llama_cpp.convert", model_path, "--outfile", output_path, "--outtype", quantization],
            capture_output=True, text=True, timeout=1800, check=True,
        )
        logger.info("model_exported_gguf", output=output_path, quantization=quantization)
        return output_path
    except FileNotFoundError as exc:
        raise RuntimeError("llama.cpp conversion tools not available; install llama-cpp-python or convert manually") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"GGUF export failed: {exc.stderr}") from exc


def export_to_safetensors(model_path: str, output_path: str) -> str:
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise ImportError("transformers not installed; run: pip install -r requirements-worker.txt") from exc

    model = AutoModelForCausalLM.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path)

    model.save_pretrained(output_path, safe_serialization=True)
    tokenizer.save_pretrained(output_path)

    logger.info("model_exported_safetensors", output=output_path)
    return output_path


def export_to_ollama_modelfile(model_path: str, output_dir: str, model_name: str, system_prompt: str | None = None) -> str:
    output_path = Path(output_dir) / "Modelfile"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"FROM {model_path}"]
    if system_prompt:
        lines.append(f'SYSTEM """{system_prompt}"""')
    lines.append("PARAMETER temperature 0.7")
    lines.append("PARAMETER top_p 0.9")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("ollama_modelfile_created", path=str(output_path), model_name=model_name)
    return str(output_path)


def package_adapter_for_distribution(adapter_path: str, output_archive_path: str) -> str:
    base_name = output_archive_path.removesuffix(".zip").removesuffix(".tar.gz")
    archive_format = "zip" if output_archive_path.endswith(".zip") else "gztar"
    result_path = shutil.make_archive(base_name, archive_format, root_dir=adapter_path)
    logger.info("adapter_packaged", archive=result_path)
    return result_path
