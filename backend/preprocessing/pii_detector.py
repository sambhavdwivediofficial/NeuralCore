from __future__ import annotations

import enum
import re

from pydantic import BaseModel


class PIIType(str, enum.Enum):
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    IP_ADDRESS = "ip_address"
    API_KEY = "api_key"
    IBAN = "iban"
    URL = "url"


class PIIMatch(BaseModel):
    type: PIIType
    value: str
    start: int
    end: int


_PATTERNS: dict[PIIType, re.Pattern[str]] = {
    PIIType.EMAIL: re.compile(
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
    ),

    PIIType.PHONE: re.compile(
        r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\d{10}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b"
    ),

    PIIType.CREDIT_CARD: re.compile(
        r"\b(?:\d[ -]*?){13,19}\b"
    ),

    PIIType.SSN: re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"
    ),

    PIIType.IP_ADDRESS: re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d{1,2})\.){3}"
        r"(?:25[0-5]|2[0-4]\d|1?\d{1,2})\b"
    ),

    PIIType.API_KEY: re.compile(
        r"\b(?:sk|pk|rk|nc)-[A-Za-z0-9]{20,}\b"
    ),

    PIIType.IBAN: re.compile(
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"
    ),

    PIIType.URL: re.compile(
        r"https?://[^\s<>\"']+"
    ),
}


_REDACTION_LABELS: dict[PIIType, str] = {
    PIIType.EMAIL: "[EMAIL]",
    PIIType.PHONE: "[PHONE]",
    PIIType.CREDIT_CARD: "[CREDIT_CARD]",
    PIIType.SSN: "[SSN]",
    PIIType.IP_ADDRESS: "[IP_ADDRESS]",
    PIIType.API_KEY: "[API_KEY]",
    PIIType.IBAN: "[IBAN]",
    PIIType.URL: "[URL]",
}


def _luhn_checksum(digits: str) -> bool:
    total = 0

    for index, char in enumerate(reversed(digits)):
        digit = int(char)

        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9

        total += digit

    return total % 10 == 0


def detect_pii(
    text: str,
    types: set[PIIType] | None = None,
) -> list[PIIMatch]:

    target_types = types or set(PIIType)
    raw_matches: list[PIIMatch] = []

    for pii_type in target_types:

        pattern = _PATTERNS.get(pii_type)

        if pattern is None:
            continue

        for match in pattern.finditer(text):

            value = match.group(0)

            if pii_type == PIIType.CREDIT_CARD:

                digits = re.sub(r"\D", "", value)

                if not (13 <= len(digits) <= 19):
                    continue

                if not _luhn_checksum(digits):
                    continue

            elif pii_type == PIIType.PHONE:

                digits = re.sub(r"\D", "", value)

                if len(digits) < 10:
                    continue

            raw_matches.append(
                PIIMatch(
                    type=pii_type,
                    value=value,
                    start=match.start(),
                    end=match.end(),
                )
            )

    priority = {
        PIIType.CREDIT_CARD: 100,
        PIIType.EMAIL: 90,
        PIIType.API_KEY: 80,
        PIIType.IBAN: 70,
        PIIType.SSN: 60,
        PIIType.IP_ADDRESS: 50,
        PIIType.URL: 40,
        PIIType.PHONE: 30,
    }

    raw_matches.sort(
        key=lambda m: (
            m.start,
            -priority.get(m.type, 0),
            -(m.end - m.start),
        )
    )

    resolved: list[PIIMatch] = []

    for candidate in raw_matches:

        overlapping = False

        for existing in resolved:

            if (
                candidate.start < existing.end
                and candidate.end > existing.start
            ):
                overlapping = True
                break

        if not overlapping:
            resolved.append(candidate)

    resolved.sort(key=lambda m: m.start)

    return resolved


def redact_pii(
    text: str,
    types: set[PIIType] | None = None,
    mask: str | None = None,
) -> str:

    matches = detect_pii(text, types)

    if not matches:
        return text

    result: list[str] = []
    cursor = 0

    for match in matches:

        if match.start < cursor:
            continue

        result.append(text[cursor:match.start])

        result.append(
            mask
            if mask is not None
            else _REDACTION_LABELS.get(match.type, "[REDACTED]")
        )

        cursor = match.end

    result.append(text[cursor:])

    return "".join(result)


def contains_pii(
    text: str,
    types: set[PIIType] | None = None,
) -> bool:
    return bool(detect_pii(text, types))


def pii_type_counts(
    text: str,
    types: set[PIIType] | None = None,
) -> dict[str, int]:

    counts: dict[str, int] = {}

    for match in detect_pii(text, types):
        counts[match.type.value] = counts.get(match.type.value, 0) + 1

    return counts
