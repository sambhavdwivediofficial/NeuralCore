# a2a/channels/broadcast.py
from __future__ import annotations

from typing import Any, Callable, Coroutine

from a2a.message import A2AMessage
from a2a.transport import A2ATransport
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.channels.broadcast")

MessageCallback = Callable[[A2AMessage], Coroutine[Any, Any, None]]


class BroadcastChannel:
    def __init__(self, transport: A2ATransport) -> None:
        self.transport = transport
        self._callbacks: list[MessageCallback] = []

    async def publish(self, message: A2AMessage) -> bool:
        return await self.transport.broadcast(message)

    async def subscribe(self, callback: MessageCallback) -> None:
        self._callbacks.append(callback)
        await self.transport.subscribe_broadcast(callback)
        logger.debug("broadcast_subscriber_added")

    async def unsubscribe(self, callback: MessageCallback) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            