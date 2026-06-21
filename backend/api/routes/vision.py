# api/routes/vision.py
from __future__ import annotations

import base64
import io
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_app_settings
from settings import Settings

router = APIRouter()

_SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}
_MAX_IMAGE_SIZE = 15 * 1024 * 1024


class ImageQueryResponse(BaseModel):
    extracted_text: str
    description: str
    answer: str


@router.post("/analyze")
async def analyze_image(
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
    file: UploadFile = File(...),
    question: Optional[str] = Query(default=None),
    extract_text: bool = Query(default=True),
) -> ImageQueryResponse:
    from pathlib import Path

    suffix = Path(file.filename or "image.png").suffix.lower()
    if suffix not in _SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported image format '{suffix}'. Supported: {sorted(_SUPPORTED_IMAGE_FORMATS)}")

    content = await file.read()
    if len(content) > _MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image exceeds 15MB limit")

    import asyncio

    ocr_text, image_metadata = await asyncio.to_thread(_run_ocr, content, extract_text)

    from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
    from model_gateway.provider_factory import get_model_gateway

    gateway = get_model_gateway(settings)

    description_prompt = (
        f"An image was uploaded (dimensions: {image_metadata.get('width')}x{image_metadata.get('height')}). "
        f"{'Text extracted from the image via OCR: ' + ocr_text.strip() if ocr_text.strip() else 'No text was detected in the image via OCR.'}\n\n"
        "Based on this information, provide a brief, useful description of what this image likely contains "
        "(e.g. a screenshot, diagram, chart, document scan, photo). Be concise."
    )
    description_response = await gateway.chat_completion(
        CompletionRequest(messages=[ChatMessage(role=ChatRole.USER, content=description_prompt)], max_tokens=256, temperature=0.3)
    )
    description = (description_response.content or "").strip()

    answer = ""
    if question:
        qa_prompt = (
            f"Image context:\n"
            f"- Description: {description}\n"
            f"- OCR extracted text: {ocr_text.strip() or '(none detected)'}\n\n"
            f"Question about the image: {question}\n\n"
            "Answer the question based on the available image information. If the OCR text and description "
            "aren't sufficient to answer confidently, say so clearly rather than guessing."
        )
        answer_response = await gateway.chat_completion(
            CompletionRequest(messages=[ChatMessage(role=ChatRole.USER, content=qa_prompt)], max_tokens=512, temperature=0.2)
        )
        answer = (answer_response.content or "").strip()

    return ImageQueryResponse(extracted_text=ocr_text.strip(), description=description, answer=answer)


@router.post("/ocr")
async def extract_text_only(
    user: CurrentUser,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    from pathlib import Path

    suffix = Path(file.filename or "image.png").suffix.lower()
    if suffix not in _SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported image format '{suffix}'")

    content = await file.read()
    import asyncio

    ocr_text, metadata = await asyncio.to_thread(_run_ocr, content, True)

    return {"extracted_text": ocr_text.strip(), "character_count": len(ocr_text.strip()), "image_metadata": metadata}


def _run_ocr(content: bytes, extract_text: bool) -> tuple[str, dict[str, Any]]:
    from PIL import Image

    image = Image.open(io.BytesIO(content))
    metadata = {"width": image.width, "height": image.height, "format": image.format}

    if not extract_text:
        return "", metadata

    try:
        import pytesseract

        return pytesseract.image_to_string(image), metadata
    except ImportError:
        return "", metadata
    except Exception:
        return "", metadata
