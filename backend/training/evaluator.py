# training/evaluator.py
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.training.evaluator")


@dataclass(slots=True)
class PretrainEvalResult:
    perplexity: float
    eval_loss: float
    tokens_evaluated: int
    duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "perplexity": round(self.perplexity, 4),
            "eval_loss": round(self.eval_loss, 4),
            "tokens_evaluated": self.tokens_evaluated,
            "duration_seconds": round(self.duration_seconds, 2),
        }


async def evaluate_perplexity(model_path: str, eval_data_path: str, max_seq_length: int = 2048, batch_size: int = 4) -> PretrainEvalResult:
    try:
        import torch
        from datasets import load_dataset
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise ImportError("torch/transformers/datasets not installed; run: pip install -r requirements-worker.txt") from exc

    def _run_sync() -> PretrainEvalResult:
        import time
        start = time.perf_counter()

        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.bfloat16, device_map="auto")
        model.eval()

        dataset = load_dataset("json", data_files={"eval": eval_data_path}, split="eval")
        total_loss = 0.0
        total_tokens = 0

        with torch.no_grad():
            for i in range(0, len(dataset), batch_size):
                batch_texts = [dataset[j]["text"] for j in range(i, min(i + batch_size, len(dataset)))]
                inputs = tokenizer(batch_texts, return_tensors="pt", truncation=True, max_length=max_seq_length, padding=True).to(model.device)
                outputs = model(**inputs, labels=inputs["input_ids"])
                num_tokens = inputs["attention_mask"].sum().item()
                total_loss += outputs.loss.item() * num_tokens
                total_tokens += num_tokens

        avg_loss = total_loss / max(total_tokens, 1)
        perplexity = math.exp(min(avg_loss, 20))

        return PretrainEvalResult(perplexity=perplexity, eval_loss=avg_loss, tokens_evaluated=total_tokens, duration_seconds=time.perf_counter() - start)

    return await asyncio.to_thread(_run_sync)


async def benchmark_inference_throughput(model_path: str, prompt: str, num_runs: int = 5, max_new_tokens: int = 128) -> dict[str, Any]:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise ImportError("torch/transformers not installed; run: pip install -r requirements-worker.txt") from exc

    def _run_sync() -> dict[str, Any]:
        import time

        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.bfloat16, device_map="auto")
        model.eval()

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        latencies: list[float] = []

        with torch.no_grad():
            model.generate(**inputs, max_new_tokens=10)

            for _ in range(num_runs):
                start = time.perf_counter()
                output = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
                latencies.append(time.perf_counter() - start)

        avg_latency = sum(latencies) / len(latencies)
        tokens_per_second = max_new_tokens / avg_latency

        return {
            "avg_latency_seconds": round(avg_latency, 4),
            "tokens_per_second": round(tokens_per_second, 2),
            "num_runs": num_runs,
            "max_new_tokens": max_new_tokens,
        }

    return await asyncio.to_thread(_run_sync)
