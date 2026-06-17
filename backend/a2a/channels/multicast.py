# a2a/channels/multicast.py
from __future__ import annotations

import asyncio
from typing import Any

from a2a.broker import A2ABroker
from a2a.message import A2AMessage
from a2a.registry import A2ARegistry
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.channels.multicast")


class MulticastChannel:
    def __init__(self, group_id: str, broker: A2ABroker) -> None:
        self.group_id = group_id
        self.broker = broker
        self.registry: A2ARegistry = broker.registry
        self._members: set[str] = set()

    def add_member(self, agent_id: str) -> None:
        self._members.add(agent_id)

    def remove_member(self, agent_id: str) -> None:
        self._members.discard(agent_id)

    async def send_to_group(
        self,
        message: A2AMessage,
        exclude_sender: bool = True,
    ) -> dict[str, bool]:
        targets = list(self._members)
        if exclude_sender:
            targets = [t for t in targets if t != message.sender_id]
        if not targets:
            return {}
        return await self.broker.fanout(message, targets)

    async def send_to_type(
        self, message: A2AMessage, agent_type: str
    ) -> dict[str, bool]:
        records = await self.registry.find_by_type(agent_type)
        agent_ids = [r.agent_id for r in records if r.agent_id != message.sender_id]
        if not agent_ids:
            return {}
        return await self.broker.fanout(message, agent_ids)
    