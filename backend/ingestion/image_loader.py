# ingestion/image_loader.py
from __future__ import annotations

import base64
import io
from typing import Any

from ingestion.base_loader import BaseLoader, LoaderError, SourceType
from ingestion.loader_factory import register_loader

_SUPPORTED_IMAGE_FORMATS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"})


@register_loader(SourceType.OTHER if not hasattr(SourceType, "IMAGE") else SourceType.IMAGE)
class ImageLoader(BaseLoader):
    source_type = SourceType.OTHER

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        import asyncio

        raw_bytes = await self._read_bytes(source_config)
        file_path = source_config.get("file_path", "image.png")
        extract_text = source_config.get("extract_text", True)
        describe_with_vision = source_config.get("describe_with_vision", False)

        ocr_text, image_metadata = await asyncio.to_thread(self._process_image, raw_bytes, extract_text)

        description = ""
        if describe_with_vision:
            description = await self._describe_with_vision_model(raw_bytes)

        combined_text_parts = []
        if description:
            combined_text_parts.append(f"Image description: {description}")
        if ocr_text.strip():
            combined_text_parts.append(f"Text found in image (OCR):\n{ocr_text.strip()}")

        combined_text = "\n\n".join(combined_text_parts) if combined_text_parts else "[Image with no extractable text or description]"

        return [
            self._build_document(
                combined_text,
                metadata={
                    "source_type": "image",
                    "file_path": file_path,
                    "has_ocr_text": bool(ocr_text.strip()),
                    "has_vision_description": bool(description),
                    **image_metadata,
                },
                source_id=file_path,
            )
        ]

    @staticmethod
    def _process_image(raw_bytes: bytes, extract_text: bool) -> tuple[str, dict[str, Any]]:
        from PIL import Image

        image = Image.open(io.BytesIO(raw_bytes))
        metadata = {"width": image.width, "height": image.height, "format": image.format}

        ocr_text = ""
        if extract_text:
            try:
                import pytesseract

                ocr_text = pytesseract.image_to_string(image)
            except ImportError:
                pass
            except Exception:
                pass

        return ocr_text, metadata

    async def _describe_with_vision_model(self, raw_bytes: bytes) -> str:
        from settings import get_settings

        settings = get_settings()
        try:
            from model_gateway.provider_factory import get_model_gateway
            from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest

            gateway = get_model_gateway(settings)
            b64_image = base64.b64encode(raw_bytes).decode("utf-8")

            response = await gateway.chat_completion(
                CompletionRequest(
                    messages=[
                        ChatMessage(
                            role=ChatRole.USER,
                            content=f"[IMAGE_BASE64:{b64_image[:100]}...] Describe this image in detail, including any diagrams, charts, UI elements, or visual structure.",
                        )
                    ],
                    max_tokens=512,
                )
            )
            return (response.content or "").strip()
        except Exception:
            return ""
