# evaluation/report_generator.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.evaluation.report")


class EvaluationReport:
    def __init__(
        self,
        report_type: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.report_type = report_type
        self.name = name
        self.metadata = metadata or {}
        self.sections: list[dict[str, Any]] = []
        self.summary: dict[str, Any] = {}
        self.generated_at = datetime.now(timezone.utc).isoformat()

    def add_section(self, title: str, data: Any, section_type: str = "table") -> None:
        self.sections.append({"title": title, "type": section_type, "data": data})

    def set_summary(self, summary: dict[str, Any]) -> None:
        self.summary = summary

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_type": self.report_type,
            "name": self.name,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "sections": self.sections,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, default=str)

    def to_markdown(self) -> str:
        lines: list[str] = [
            f"# Evaluation Report: {self.name}",
            f"**Type:** {self.report_type}",
            f"**Generated:** {self.generated_at}",
            "",
            "## Summary",
        ]
        for key, value in self.summary.items():
            if isinstance(value, float):
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value:.4f}")
            else:
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")

        for section in self.sections:
            lines.append(f"\n## {section['title']}")
            data = section["data"]
            if isinstance(data, list) and data and isinstance(data[0], dict):
                headers = list(data[0].keys())
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("|" + "|".join(["---"] * len(headers)) + "|")
                for row in data:
                    row_values = [str(row.get(h, "")) for h in headers]
                    lines.append("| " + " | ".join(row_values) + " |")
            elif isinstance(data, dict):
                for k, v in data.items():
                    lines.append(f"- **{k}**: {v}")
            else:
                lines.append(str(data))

        return "\n".join(lines)


def build_retrieval_eval_report(eval_results: dict[str, Any]) -> EvaluationReport:
    report = EvaluationReport("retrieval_evaluation", "Retrieval Quality Evaluation")
    report.set_summary({
        "total_queries": eval_results.get("total_queries", 0),
        "avg_ndcg_at_10": eval_results.get("avg_ndcg_at_10", 0.0),
        "avg_mrr": eval_results.get("avg_mrr", 0.0),
        "avg_precision_at_10": eval_results.get("avg_precision_at_10", 0.0),
        "avg_recall_at_10": eval_results.get("avg_recall_at_10", 0.0),
        "avg_latency_ms": eval_results.get("avg_latency_ms", 0.0),
    })
    per_query = eval_results.get("per_query_results", [])
    if per_query:
        report.add_section("Per-Query Results", per_query, "table")
    return report


def build_rag_eval_report(eval_results: dict[str, Any]) -> EvaluationReport:
    report = EvaluationReport("rag_evaluation", "RAG Pipeline Quality Evaluation")
    report.set_summary({
        "total_samples": eval_results.get("total_samples", 0),
        "valid_samples": eval_results.get("valid_samples", 0),
        "avg_composite_score": eval_results.get("avg_composite_score", 0.0),
        "avg_context_relevance": eval_results.get("avg_context_relevance", 0.0),
        "avg_faithfulness": eval_results.get("avg_faithfulness", 0.0),
        "avg_answer_relevance": eval_results.get("avg_answer_relevance", 0.0),
        "avg_latency_ms": eval_results.get("avg_latency_ms", 0.0),
    })
    per_sample = eval_results.get("per_sample_results", [])
    if per_sample:
        report.add_section("Per-Sample Results", per_sample, "table")
    return report


def build_benchmark_report(benchmark_result: Any) -> EvaluationReport:
    result_dict = benchmark_result.to_dict() if hasattr(benchmark_result, "to_dict") else benchmark_result
    report = EvaluationReport("benchmark", f"Benchmark: {result_dict.get('name', 'unknown')}")
    report.set_summary({k: v for k, v in result_dict.items() if k not in ("metadata",)})
    return report
