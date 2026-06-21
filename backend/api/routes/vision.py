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
    use_vision: bool = Query(default=True),
) -> ImageQueryResponse:
    from pathlib import Path

    suffix = Path(file.filename or "image.png").suffix.lower()
    if suffix not in _SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported image format '{suffix}'. Supported: {sorted(_SUPPORTED_IMAGE_FORMATS)}")

    content = await file.read()
    if len(content) > _MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image exceeds 15MB limit")

    from ingestion.image_loader import ImageLoader

    loader = ImageLoader(settings)
    documents = await loader.load({
        "content_base64": __import__("base64").b64encode(content).decode("utf-8"),
        "file_path": file.filename or "image.png",
        "extract_text": extract_text,
        "use_vision": use_vision,
    })

    doc = documents[0]
    ocr_text = ""
    vision_description = ""
    for part in doc["text"].split("\n\n"):
        if part.startswith("Text extracted from image (OCR):"):
            ocr_text = part.replace("Text extracted from image (OCR):\n", "")
        elif part.startswith("Visual description (from vision model):"):
            vision_description = part.replace("Visual description (from vision model):\n", "")

    from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
    from model_gateway.provider_factory import get_model_gateway

    answer = ""
    if question:
        gateway = get_model_gateway(settings)
        qa_prompt = (
            f"Image context:\n{doc['text']}\n\n"
            f"Question about the image: {question}\n\n"
            "Answer using only the information available above. If it isn't sufficient to answer "
            "confidently, say so clearly rather than guessing."
        )
        answer_response = await gateway.chat_completion(
            CompletionRequest(messages=[ChatMessage(role=ChatRole.USER, content=qa_prompt)], max_tokens=512, temperature=0.2)
        )
        answer = (answer_response.content or "").strip()

    return ImageQueryResponse(extracted_text=ocr_text.strip(), description=vision_description.strip(), answer=answer)


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
