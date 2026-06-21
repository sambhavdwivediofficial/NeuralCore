# api/routes/voice.py
from __future__ import annotations

import base64
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_app_settings
from settings import Settings

router = APIRouter()

_SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac"}
_DEFAULT_TTS_VOICE = "hi-IN-AmayaNeural"
_AVAILABLE_VOICES = [
    {"id": "en-US-AriaNeural", "name": "Aria (US, Female)", "language": "en-US"},
    {"id": "en-US-GuyNeural", "name": "Guy (US, Male)", "language": "en-US"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (UK, Female)", "language": "en-GB"},
    {"id": "en-IN-NeerjaNeural", "name": "Neerja (India, Female)", "language": "en-IN"},
    {"id": "en-IN-PrabhatNeural", "name": "Prabhat (India, Male)", "language": "en-IN"},
    {"id": "hi-IN-AmayaNeural", "name": "Amaya (Hindi, Female)", "language": "hi-IN"},
    {"id": "hi-IN-MadhurNeural", "name": "Madhur (Hindi, Male)", "language": "hi-IN"},
]


class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = _DEFAULT_TTS_VOICE
    rate: str = "+0%"
    pitch: str = "+0Hz"


class VoiceQueryResponse(BaseModel):
    transcript: str
    answer: str
    audio_base64: Optional[str] = None
    sources: list[dict[str, Any]] = []


@router.get("/voices")
async def list_voices() -> list[dict[str, Any]]:
    return _AVAILABLE_VOICES


@router.post("/transcribe")
async def transcribe_audio(
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
    file: UploadFile = File(...),
    language: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    suffix = Path(file.filename or "audio.wav").suffix.lower()
    if suffix not in _SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{suffix}'. Supported: {sorted(_SUPPORTED_AUDIO_FORMATS)}",
        )

    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file exceeds 25MB limit")

    from ingestion.audio_loader import AudioLoader

    loader = AudioLoader(settings)
    documents = await loader.load({
        "content_base64": base64.b64encode(content).decode("utf-8"),
        "file_path": file.filename or "audio.wav",
        "whisper_model": "base",
        "language": language,
    })

    if not documents:
        return {"transcript": "", "detected_language": None, "confidence": 0.0}

    doc = documents[0]
    return {
        "transcript": doc["text"],
        "detected_language": doc["metadata"].get("detected_language"),
        "duration_seconds": doc["metadata"].get("duration_seconds"),
    }


@router.post("/speak")
async def text_to_speech(body: TextToSpeechRequest, user: CurrentUser) -> StreamingResponse:
    try:
        import edge_tts
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS engine not installed; run: pip install edge-tts (requirements-worker.txt)",
        ) from exc

    if not body.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text cannot be empty")
    if len(body.text) > 5000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text exceeds 5000 character limit per request")

    async def _audio_stream():
        communicator = edge_tts.Communicate(body.text, voice=body.voice, rate=body.rate, pitch=body.pitch)
        async for chunk in communicator.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    return StreamingResponse(_audio_stream(), media_type="audio/mpeg")


@router.post("/query", response_model=VoiceQueryResponse)
async def voice_query(
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
    file: UploadFile = File(...),
    knowledge_base_id: Optional[str] = Query(default=None),
    voice: str = Query(default=_DEFAULT_TTS_VOICE),
    return_audio: bool = Query(default=True),
    language: Optional[str] = Query(default=None),
) -> VoiceQueryResponse:
    suffix = Path(file.filename or "audio.wav").suffix.lower()
    if suffix not in _SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported audio format '{suffix}'")

    content = await file.read()

    from ingestion.audio_loader import AudioLoader

    loader = AudioLoader(settings)
    transcribed = await loader.load({
        "content_base64": base64.b64encode(content).decode("utf-8"),
        "file_path": file.filename or "audio.wav",
        "whisper_model": "base",
        "language": language,
    })

    if not transcribed or not transcribed[0]["text"].strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Could not transcribe any speech from the audio")

    transcript = transcribed[0]["text"]

    from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
    from model_gateway.provider_factory import get_model_gateway
    from prompt_engine.template_engine import default_registry

    sources: list[dict[str, Any]] = []
    answer_text: str

    if knowledge_base_id:
        import uuid as _uuid

        from retrieval.retriever import Retriever

        retriever = Retriever(settings=settings)
        results = await retriever.search(
            knowledge_base_id=_uuid.UUID(knowledge_base_id),
            query=transcript,
            top_k=5,
            use_hybrid=True,
            use_reranking=True,
        )
        context = "\n\n".join(r.text or "" for r in results if r.text)
        sources = [{"id": r.id, "score": r.score, "metadata": r.metadata} for r in results]

        gateway = get_model_gateway(settings)
        user_content = default_registry.render("rag_qa", context=context, question=transcript)
        response = await gateway.chat_completion(
            CompletionRequest(messages=[ChatMessage(role=ChatRole.USER, content=user_content)], max_tokens=512, temperature=0.3)
        )
        answer_text = (response.content or "").strip()
    else:
        gateway = get_model_gateway(settings)
        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[
                    ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful, concise voice assistant. Keep answers conversational and brief."),
                    ChatMessage(role=ChatRole.USER, content=transcript),
                ],
                max_tokens=512,
                temperature=0.5,
            )
        )
        answer_text = (response.content or "").strip()

    audio_base64: Optional[str] = None
    if return_audio and answer_text:
        try:
            import edge_tts

            audio_chunks: list[bytes] = []
            communicator = edge_tts.Communicate(answer_text[:5000], voice=voice)
            async for chunk in communicator.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            audio_base64 = base64.b64encode(b"".join(audio_chunks)).decode("utf-8")
        except ImportError:
            audio_base64 = None

    return VoiceQueryResponse(transcript=transcript, answer=answer_text, audio_base64=audio_base64, sources=sources)
