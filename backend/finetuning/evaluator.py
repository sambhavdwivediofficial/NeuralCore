# finetuning/evaluator.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.finetuning.evaluator")


@dataclass(slots=True)
class FineTuneEvalSample:
    prompt: str
    expected_output: str


@dataclass(slots=True)
class FineTuneEvalResult:
    total_samples: int
    avg_perplexity: float | None
    avg_bleu_score: float
    avg_exact_match_rate: float
    sample_outputs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "avg_perplexity": self.avg_perplexity,
            "avg_bleu_score": round(self.avg_bleu_score, 4),
            "avg_exact_match_rate": round(self.avg_exact_match_rate, 4),
            "sample_outputs": self.sample_outputs[:10],
        }


def _simple_bleu(reference: str, candidate: str, n: int = 4) -> float:
    ref_tokens = reference.lower().split()
    cand_tokens = candidate.lower().split()
    if not cand_tokens:
        return 0.0

    precisions: list[float] = []
    for order in range(1, n + 1):
        ref_ngrams = [tuple(ref_tokens[i : i + order]) for i in range(len(ref_tokens) - order + 1)]
        cand_ngrams = [tuple(cand_tokens[i : i + order]) for i in range(len(cand_tokens) - order + 1)]
        if not cand_ngrams:
            precisions.append(0.0)
            continue
        from collections import Counter
        ref_counts = Counter(ref_ngrams)
        cand_counts = Counter(cand_ngrams)
        matches = sum(min(count, ref_counts.get(gram, 0)) for gram, count in cand_counts.items())
        precisions.append(matches / len(cand_ngrams))

    if any(p == 0 for p in precisions):
        return 0.0

    import math
    geo_mean = math.exp(sum(math.log(p) for p in precisions) / len(precisions))
    brevity_penalty = min(1.0, math.exp(1 - len(ref_tokens) / max(len(cand_tokens), 1)))
    return geo_mean * brevity_penalty


async def evaluate_finetuned_model(
    model_path: str,
    eval_samples: list[FineTuneEvalSample],
    base_model_for_tokenizer: str | None = None,
) -> FineTuneEvalResult:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise ImportError("transformers/torch not installed; run: pip install -r requirements-worker.txt") from exc

    def _run_sync() -> FineTuneEvalResult:
        tokenizer = AutoTokenizer.from_pretrained(base_model_for_tokenizer or model_path)
        model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.bfloat16, device_map="auto")
        model.eval()

        bleu_scores: list[float] = []
        exact_matches = 0
        sample_outputs: list[dict[str, Any]] = []

        with torch.no_grad():
            for sample in eval_samples:
                inputs = tokenizer(sample.prompt, return_tensors="pt").to(model.device)
                output_ids = model.generate(**inputs, max_new_tokens=256, do_sample=False)
                generated = tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

                bleu = _simple_bleu(sample.expected_output, generated)
                bleu_scores.append(bleu)

                if generated.strip().lower() == sample.expected_output.strip().lower():
                    exact_matches += 1

                sample_outputs.append({"prompt": sample.prompt[:100], "expected": sample.expected_output[:100], "generated": generated[:100], "bleu": round(bleu, 4)})

        return FineTuneEvalResult(
            total_samples=len(eval_samples),
            avg_perplexity=None,
            avg_bleu_score=sum(bleu_scores) / len(bleu_scores) if bleu_scores else 0.0,
            avg_exact_match_rate=exact_matches / len(eval_samples) if eval_samples else 0.0,
            sample_outputs=sample_outputs,
        )

    return await asyncio.to_thread(_run_sync)
