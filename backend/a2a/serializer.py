# a2a/serializer.py
from __future__ import annotations

import json
import zlib
from typing import Any

from a2a.message import A2AMessage


class SerializationError(ValueError):
    pass


class A2ASerializer:
    _MAGIC = b"\xA2\xA0"
    _VERSION = 1
    _COMPRESS_THRESHOLD = 1024

    @staticmethod
    def to_json(message: A2AMessage) -> str:
        try:
            return json.dumps(message.to_dict(), separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise SerializationError(f"JSON serialization failed: {exc}") from exc

    @staticmethod
    def from_json(data: str) -> A2AMessage:
        try:
            return A2AMessage.from_dict(json.loads(data))
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise SerializationError(f"JSON deserialization failed: {exc}") from exc

    @classmethod
    def to_bytes(cls, message: A2AMessage) -> bytes:
        raw = A2ASerializer.to_json(message).encode("utf-8")
        if len(raw) >= cls._COMPRESS_THRESHOLD:
            compressed = zlib.compress(raw, level=6)
            flag = b"\x01"
            payload = compressed
        else:
            flag = b"\x00"
            payload = raw
        return cls._MAGIC + bytes([cls._VERSION]) + flag + payload

    @classmethod
    def from_bytes(cls, data: bytes) -> A2AMessage:
        if len(data) < 4 or data[:2] != cls._MAGIC:
            raise SerializationError("Invalid A2A message magic bytes")
        _version = data[2]
        is_compressed = data[3] == 0x01
        payload = data[4:]
        if is_compressed:
            try:
                payload = zlib.decompress(payload)
            except zlib.error as exc:
                raise SerializationError(f"Decompression failed: {exc}") from exc
        return A2ASerializer.from_json(payload.decode("utf-8"))

    @staticmethod
    def batch_serialize(messages: list[A2AMessage]) -> str:
        return json.dumps([msg.to_dict() for msg in messages], separators=(",", ":"))

    @staticmethod
    def batch_deserialize(data: str) -> list[A2AMessage]:
        try:
            items = json.loads(data)
            return [A2AMessage.from_dict(item) for item in items]
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise SerializationError(f"Batch deserialization failed: {exc}") from exc
        