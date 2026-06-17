# a2a/router.py
from __future__ import annotations

from typing import Any

from a2a.broker import A2ABroker
from a2a.message import A2AMessage, A2AMessageType
from a2a.protocol import A2AProtocol, CommunicationPattern
from a2a.registry import A2ARegistry
from a2a.validator import validate_message
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.router")


class RoutingRule:
    __slots__ = ("condition", "target_type", "target_capability", "pattern")

    def __init__(
        self,
        condition: Any,
        target_type: str | None = None,
        target_capability: str | None = None,
        pattern: CommunicationPattern = CommunicationPattern.DIRECT,
    ) -> None:
        self.condition = condition
        self.target_type = target_type
        self.target_capability = target_capability
        self.pattern = pattern


class A2ARouter:
    def __init__(self, broker: A2ABroker) -> None:
        self.broker = broker
        self.registry: A2ARegistry = broker.registry
        self._rules: list[RoutingRule] = []

    def add_rule(self, rule: RoutingRule) -> None:
        self._rules.append(rule)

    async def route(
        self,
        message: A2AMessage,
        pattern: CommunicationPattern = CommunicationPattern.DIRECT,
    ) -> bool:
        validation = validate_message(message)
        if not validation.valid:
            logger.warning("routing_validation_failed", errors=validation.errors)
            return False

        if pattern == CommunicationPattern.DIRECT:
            if message.recipient_id is None:
                logger.warning("direct_routing_missing_recipient", message_id=message.message_id)
                return False
            return await self.broker.send(message)

        if pattern == CommunicationPattern.BROADCAST:
            return await self.broker.transport.broadcast(message)

        if pattern == CommunicationPattern.MULTICAST:
            target_type = message.metadata.get("target_type")
            if not target_type:
                return False
            targets = await self.registry.find_by_type(target_type)
            agent_ids = [t.agent_id for t in targets if t.agent_id != message.sender_id]
            if not agent_ids:
                return False
            results = await self.broker.fanout(message, agent_ids)
            return any(results.values())

        if pattern == CommunicationPattern.QUEUE:
            target_type = message.metadata.get("target_type") or message.recipient_type
            if not target_type:
                return False
            return await self.broker.send_to_type(message, target_type)

        if pattern == CommunicationPattern.ROUND_ROBIN:
            target_type = message.metadata.get("target_type") or message.recipient_type
            if not target_type:
                return False
            agents = await self.registry.find_by_type(target_type)
            if not agents:
                return False
            sorted_agents = sorted(agents, key=lambda a: a.last_seen)
            message.recipient_id = sorted_agents[0].agent_id
            return await self.broker.send(message)

        return False

    async def route_by_capability(
        self, message: A2AMessage, capability: str
    ) -> bool:
        return await self.broker.send_with_capability(message, capability)

    async def pipeline(
        self,
        initial_message: A2AMessage,
        agent_ids: list[str],
        timeout_per_step: float = 30.0,
    ) -> list[A2AMessage]:
        results: list[A2AMessage] = []
        current = initial_message

        for agent_id in agent_ids:
            current.recipient_id = agent_id
            response = await self.broker.request_response(current, timeout=timeout_per_step)
            if response is None:
                logger.warning("pipeline_step_timeout", agent_id=agent_id, step=len(results))
                break
            results.append(response)
            current = response.create_reply(
                sender_id=response.recipient_id or initial_message.sender_id,
                content=response.content,
            )

        return results
    