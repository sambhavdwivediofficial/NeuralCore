# a2a/channels/direct.py
from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine

from a2a.message import A2AMessage
from a2a.transport import A2ATransport
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.channels.direct")

MessageCallback = Callable[[A2AMessage], Coroutine[Any, Any, None]]


class DirectChannel:
    def __init__(self, agent_id: str, transport: A2ATransport) -> None:
        self.agent_id = agent_id
        self.transport = transport
        self._active = False

    async def open(self, callback: MessageCallback) -> None:
        self._active = True
        await self.transport.subscribe(self.agent_id, callback)
        await self.transport.start_polling(self.agent_id, interval=0.3)
        logger.info("direct_channel_opened", agent_id=self.agent_id)

    async def close(self) -> None:
        self._active = False
        await self.transport.stop(self.agent_id)
        logger.info("direct_channel_closed", agent_id=self.agent_id)

    async def send(self, message: A2AMessage) -> bool:
        if not self._active:
            logger.warning("direct_channel_not_open", agent_id=self.agent_id)
            return False
        return await self.transport.send(message)

    async def receive_once(self, timeout: float = 10.0) -> A2AMessage | None:
        received: list[A2AMessage] = []

        async def _cb(msg: A2AMessage) -> None:
            received.append(msg)

        await self.transport.subscribe(self.agent_id, _cb)
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            if received:
                return received[0]
            await asyncio.sleep(0.1)
        return None
    