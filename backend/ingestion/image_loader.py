# ingestion/image_loader.py
from __future__ import annotations

import io
from typing import Any

from ingestion.base_loader import BaseLoader, SourceType
from ingestion.loader_factory import register_loader
from monitoring.logging import get_logger

logger = get_logger("neuralcore.ingestion.image_loader")

_SUPPORTED_IMAGE_FORMATS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"})
_MIN_VISION_DESCRIPTION_LENGTH = 15


@register_loader(SourceType.IMAGE)
class ImageLoader(BaseLoader):
    source_type = SourceType.IMAGE

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        import asyncio

        raw_bytes = await self._read_bytes(source_config)
        file_path = source_config.get("file_path", "image.png")
        extract_text = source_config.get("extract_text", True)
        use_vision = source_config.get("use_vision", True)

        ocr_text, image_metadata = await asyncio.to_thread(self._run_ocr, raw_bytes, extract_text)

        vision_description = ""
        vision_used = False
        if use_vision:
            vision_description, vision_used = await self._run_vision_description(raw_bytes)

        combined_text = self._merge_signals(ocr_text, vision_description)

        return [
            self._build_document(
                combined_text,
                metadata={
                    "source_type": "image",
                    "file_path": file_path,
                    "has_ocr_text": bool(ocr_text.strip()),
                    "has_vision_description": vision_used,
                    **image_metadata,
                },
                source_id=file_path,
            )
        ]

    @staticmethod
    def _run_ocr(raw_bytes: bytes, extract_text: bool) -> tuple[str, dict[str, Any]]:
        from PIL import Image

        image = Image.open(io.BytesIO(raw_bytes))
        metadata = {"width": image.width, "height": image.height, "format": image.format}

        if not extract_text:
            return "", metadata

        try:
            import pytesseract

            return pytesseract.image_to_string(image), metadata
        except ImportError:
            logger.debug("ocr_skipped_pytesseract_not_installed")
            return "", metadata
        except Exception as exc:
            logger.warning("ocr_extraction_failed", error=str(exc))
            return "", metadata

    async def _run_vision_description(self, raw_bytes: bytes) -> tuple[str, bool]:
        from settings import get_settings

        settings = get_settings()
        try:
            from model_gateway.provider_factory import get_model_provider

            provider = get_model_provider(settings, provider_name="ollama")
            has_vision = await provider.supports_vision()
            if not has_vision:
                return "", False

            description = await self._call_vision_model(provider, raw_bytes)
            if len(description.strip()) < _MIN_VISION_DESCRIPTION_LENGTH:
                logger.debug("vision_description_too_short_discarded", length=len(description.strip()))
                return "", False

            return description.strip(), True
        except Exception as exc:
            logger.warning("vision_description_failed", error=str(exc))
            return "", False

    @staticmethod
    async def _call_vision_model(provider: Any, raw_bytes: bytes) -> str:
        import base64

        import httpx

        b64_image = base64.b64encode(raw_bytes).decode("utf-8")
        base_url = (provider.config.base_url or "http://localhost:11434/v1").removesuffix("/v1")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": provider.config.default_model,
                    "prompt": (
                        "Describe this image factually and concisely: what type of image it is "
                        "(screenshot, diagram, chart, photo, document scan), its key visual elements, "
                        "layout, and any notable structure. Do not guess at text content - focus on visuals."
                    ),
                    "images": [b64_image],
                    "stream": False,
                },
            )
            if response.status_code != 200:
                return ""
            return response.json().get("response", "")

    @staticmethod
    def _merge_signals(ocr_text: str, vision_description: str) -> str:
        ocr_clean = ocr_text.strip()
        vision_clean = vision_description.strip()

        if not ocr_clean and not vision_clean:
            return "[Image with no extractable text or visual description available]"

        parts: list[str] = []
        if vision_clean:
            parts.append(f"Visual description (from vision model):\n{vision_clean}")
        if ocr_clean:
            parts.append(f"Text extracted from image (OCR):\n{ocr_clean}")

        return "\n\n".join(parts)
