# agents/coding_agent.py
from __future__ import annotations

import re
from typing import Any

from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.agents.coding_agent")

_CODING_SYSTEM = (
    "You are an expert software engineer. Write clean, production-ready, well-structured code. "
    "Follow best practices for the language. Include proper error handling. "
    "Return only the code with minimal explanation unless specifically asked."
)

_CODE_BLOCK_PATTERN = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)


class CodingAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate_code(
        self,
        task: str,
        language: str = "python",
        context: str = "",
        existing_code: str = "",
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(self.settings)
        parts = [f"Language: {language}", f"Task: {task}"]
        if context:
            parts.append(f"Context:\n{context}")
        if existing_code:
            parts.append(f"Existing code to modify/extend:\n```{language}\n{existing_code}\n```")
        parts.append(f"Write the {language} code:")
        user_content = "\n\n".join(parts)

        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[
                    ChatMessage(role=ChatRole.SYSTEM, content=_CODING_SYSTEM),
                    ChatMessage(role=ChatRole.USER, content=user_content),
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )
        )

        raw_output = (response.content or "").strip()
        code_blocks = _CODE_BLOCK_PATTERN.findall(raw_output)
        extracted_code = code_blocks[0].strip() if code_blocks else raw_output

        return {
            "code": extracted_code,
            "language": language,
            "raw_response": raw_output,
            "has_code_block": bool(code_blocks),
        }

    async def review_code(
        self,
        code: str,
        language: str = "python",
        focus: list[str] | None = None,
    ) -> str:
        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(self.settings)
        focus_text = ", ".join(focus) if focus else "correctness, security, performance, readability"
        user_content = (
            f"Review the following {language} code for: {focus_text}\n\n"
            f"```{language}\n{code}\n```\n\n"
            "Provide specific, actionable feedback:"
        )
        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[
                    ChatMessage(role=ChatRole.SYSTEM, content=_CODING_SYSTEM),
                    ChatMessage(role=ChatRole.USER, content=user_content),
                ],
                max_tokens=1024,
                temperature=0.1,
            )
        )
        return (response.content or "").strip()
