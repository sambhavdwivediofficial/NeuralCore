# ingestion/video_loader.py
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from ingestion.base_loader import BaseLoader, LoaderError, SourceType
from ingestion.loader_factory import register_loader

_SUPPORTED_FORMATS = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"})


@register_loader(SourceType.VIDEO)
class VideoLoader(BaseLoader):
    source_type = SourceType.VIDEO

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        raw_bytes = await self._read_bytes(source_config)
        file_path = source_config.get("file_path", "video.mp4")
        suffix = Path(file_path).suffix.lower() or ".mp4"
        if suffix not in _SUPPORTED_FORMATS:
            raise LoaderError(f"unsupported video format '{suffix}'", source_type=self.source_type.value)

        model_size: str = source_config.get("whisper_model", "base")
        language: str | None = source_config.get("language")
        include_timestamps: bool = source_config.get("include_timestamps", False)

        text, extra_metadata = await asyncio.to_thread(
            self._extract_and_transcribe, raw_bytes, suffix, model_size, language, include_timestamps
        )
        return [
            self._build_document(
                text,
                metadata={"source_type": self.source_type.value, "file_path": file_path, **extra_metadata},
                source_id=file_path,
            )
        ]

    @staticmethod
    def _extract_and_transcribe(
        raw_bytes: bytes, suffix: str, model_size: str, language: str | None, include_timestamps: bool
    ) -> tuple[str, dict[str, Any]]:
        try:
            import whisper
        except ImportError as exc:
            raise LoaderError(
                "openai-whisper is not installed; install requirements-worker.txt",
                source_type=SourceType.VIDEO.value,
            ) from exc

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw_bytes)
            video_path = tmp.name

        audio_path = video_path.replace(suffix, ".wav")

        try:
            import subprocess

            subprocess.run(
                ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path],
                capture_output=True,
                check=True,
                timeout=300,
            )
            model = whisper.load_model(model_size)
            result = model.transcribe(audio_path, language=language, verbose=False)
        except subprocess.CalledProcessError as exc:
            raise LoaderError(f"ffmpeg audio extraction failed: {exc.stderr.decode()}", source_type=SourceType.VIDEO.value) from exc
        except FileNotFoundError as exc:
            raise LoaderError("ffmpeg is not installed or not in PATH", source_type=SourceType.VIDEO.value) from exc
        finally:
            Path(video_path).unlink(missing_ok=True)
            Path(audio_path).unlink(missing_ok=True)

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
            "video_format": suffix,
        }
    