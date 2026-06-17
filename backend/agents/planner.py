# agents/planner.py
from __future__ import annotations

import json
from typing import Any

from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.agents.planner")

_PLANNING_SYSTEM = (
    "You are a task planning assistant. Given a high-level task, break it down into "
    "clear, sequential, executable steps. Each step should be atomic and actionable. "
    "Return a JSON array of step objects with keys: 'step_number', 'description', 'agent_type', 'expected_output'."
)

_AGENT_TYPES = "planner, executor, retrieval, memory, research, coding, tool"


class PlannerAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_plan(
        self,
        task: str,
        context: str = "",
        max_steps: int = 10,
    ) -> list[dict[str, Any]]:
        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(self.settings)
        user_content = (
            f"Task: {task}\n\n"
            f"Context: {context}\n\n" if context else f"Task: {task}\n\n"
            f"Available agent types: {_AGENT_TYPES}\n\n"
            f"Create a plan with at most {max_steps} steps.\n"
            "Return ONLY a valid JSON array, no markdown, no explanation."
        )

        try:
            response = await gateway.chat_completion(
                CompletionRequest(
                    messages=[
                        ChatMessage(role=ChatRole.SYSTEM, content=_PLANNING_SYSTEM),
                        ChatMessage(role=ChatRole.USER, content=user_content),
                    ],
                    max_tokens=1000,
                    temperature=0.1,
                )
            )
            raw = (response.content or "").strip().strip("```json").strip("```").strip()
            steps: list[dict[str, Any]] = json.loads(raw)
            return steps[:max_steps]
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("plan_creation_failed", error=str(exc))
            return [{"step_number": 1, "description": task, "agent_type": "executor", "expected_output": "Task result"}]

    async def refine_plan(
        self,
        original_plan: list[dict[str, Any]],
        feedback: str,
    ) -> list[dict[str, Any]]:
        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(self.settings)
        plan_text = json.dumps(original_plan, indent=2)
        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[
                    ChatMessage(role=ChatRole.SYSTEM, content=_PLANNING_SYSTEM),
                    ChatMessage(role=ChatRole.USER, content=f"Original plan:\n{plan_text}\n\nFeedback: {feedback}\n\nReturn the refined plan as JSON array only."),
                ],
                max_tokens=1000,
                temperature=0.1,
            )
        )
        try:
            raw = (response.content or "").strip().strip("```json").strip("```").strip()
            return json.loads(raw)
        except (json.JSONDecodeError, Exception):
            return original_plan
