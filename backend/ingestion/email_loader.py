# ingestion/email_loader.py
from __future__ import annotations

import asyncio
import email
import email.policy
from email.message import EmailMessage
from typing import Any

from ingestion.base_loader import BaseLoader, SourceType
from ingestion.loader_factory import register_loader
from preprocessing.cleaner import CleaningOptions, clean_text

_CLEANING_OPTIONS = CleaningOptions(strip_html=True, decode_entities=True, remove_control_characters=True, normalize=True)


@register_loader(SourceType.EMAIL)
class EmailLoader(BaseLoader):
    source_type = SourceType.EMAIL

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        raw_bytes = await self._read_bytes(source_config)
        return await asyncio.to_thread(self._parse_email, raw_bytes, source_config)

    def _parse_email(self, raw_bytes: bytes, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        msg: EmailMessage = email.message_from_bytes(raw_bytes, policy=email.policy.default)
        subject = msg.get("Subject", "")
        from_addr = msg.get("From", "")
        to_addr = msg.get("To", "")
        date = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")
        source_id = message_id.strip("<>") if message_id else source_config.get("file_path")

        body_parts: list[str] = []
        attachments: list[dict[str, Any]] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in disposition:
                    attachments.append({"filename": part.get_filename(), "content_type": content_type})
                    continue
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_parts.append(payload.decode(charset, errors="replace"))
                elif content_type == "text/html" and not body_parts:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_parts.append(clean_text(payload.decode(charset, errors="replace"), _CLEANING_OPTIONS))
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                raw_body = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    body_parts.append(clean_text(raw_body, _CLEANING_OPTIONS))
                else:
                    body_parts.append(raw_body)

        body = "\n\n".join(body_parts).strip()
        if not body:
            return []

        full_text = f"Subject: {subject}\nFrom: {from_addr}\nTo: {to_addr}\nDate: {date}\n\n{body}"
        return [
            self._build_document(
                full_text,
                metadata={
                    "source_type": self.source_type.value,
                    "subject": subject,
                    "from": from_addr,
                    "to": to_addr,
                    "date": date,
                    "message_id": source_id,
                    "attachment_count": len(attachments),
                    "attachments": attachments,
                },
                source_id=source_id,
            )
        ]
    