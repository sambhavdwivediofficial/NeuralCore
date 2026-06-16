# ingestion/audio_loader.py
from __future__ import annotations

import asyncio
import io
import tempfile
from pathlib import Path
from typing import Any

from ingestion.base_loader import BaseLoader, LoaderError, SourceType
from ingestion.loader_factory import register_loader

_SUPPORTED_FORMATS = frozenset({".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus"})


@register_loader(SourceType.AUDIO)
class AudioLoader(BaseLoader):
    source_type = SourceType.AUDIO

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        raw_bytes = await self._read_bytes(source_config)
        file_path = source_config.get("file_path", "audio.mp3")
        suffix = Path(file_path).suffix.lower() or ".mp3"
        if suffix not in _SUPPORTED_FORMATS:
            raise LoaderError(f"unsupported audio format '{suffix}'", source_type=self.source_type.value)

        model_size: str = source_config.get("whisper_model", "base")
        language: str | None = source_config.get("language")
        include_timestamps: bool = source_config.get("include_timestamps", False)

        text, extra_metadata = await asyncio.to_thread(
            self._transcribe, raw_bytes, suffix, model_size, language, include_timestamps
        )
        return [
            self._build_document(
                text,
                metadata={
                    "source_type": self.source_type.value,
                    "file_path": file_path,
                    **extra_metadata,
                },
                source_id=file_path,
            )
        ]

    @staticmethod
    def _transcribe(
        raw_bytes: bytes, suffix: str, model_size: str, language: str | None, include_timestamps: bool
    ) -> tuple[str, dict[str, Any]]:
        try:
            import whisper
        except ImportError as exc:
            raise LoaderError(
                "openai-whisper is not installed; install requirements-worker.txt",
                source_type=SourceType.AUDIO.value,
            ) from exc

        model = whisper.load_model(model_size)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        try:
            result = model.transcribe(tmp_path, language=language, verbose=False)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if include_timestamps and result.get("segments"):
            text = "\n".join(
                f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text'].strip()}"
                for seg in result["segments"]
            )
        else:
            text = result.get("text", "").strip()

        return text, {
            "whisper_model": model_size,
            "detected_language": result.get("language"),
            "duration_seconds": result.get("segments", [{}])[-1].get("end") if result.get("segments") else None,
        }
    