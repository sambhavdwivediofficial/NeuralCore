# ingestion/youtube_loader.py
from __future__ import annotations

import re
from typing import Any

from ingestion.base_loader import BaseLoader, LoaderError, SourceNotFoundError, SourceType
from ingestion.loader_factory import register_loader

_YOUTUBE_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([A-Za-z0-9_\-]{11})"
)


def _extract_video_id(url: str) -> str | None:
    match = _YOUTUBE_ID_PATTERN.search(url)
    return match.group(1) if match else None


@register_loader(SourceType.YOUTUBE)
class YoutubeLoader(BaseLoader):
    source_type = SourceType.YOUTUBE

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        import asyncio

        url: str = source_config["url"]
        languages: list[str] = source_config.get("languages", ["en"])
        include_timestamps: bool = source_config.get("include_timestamps", False)

        video_id = _extract_video_id(url)
        if not video_id:
            raise LoaderError(f"could not extract video ID from URL: {url}", source_type=self.source_type.value)

        try:
            from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi
        except ImportError as exc:
            raise LoaderError(
                "youtube-transcript-api is not installed; run: pip install youtube-transcript-api",
                source_type=self.source_type.value,
            ) from exc

        try:
            transcript_list = await asyncio.to_thread(YouTubeTranscriptApi.list_transcripts, video_id)
            try:
                transcript = transcript_list.find_transcript(languages)
            except NoTranscriptFound:
                transcript = transcript_list.find_generated_transcript(languages)
            entries = await asyncio.to_thread(transcript.fetch)
        except TranscriptsDisabled as exc:
            raise SourceNotFoundError(f"transcripts are disabled for video: {url}", source_type=self.source_type.value) from exc
        except Exception as exc:
            raise LoaderError(str(exc), source_type=self.source_type.value) from exc

        if include_timestamps:
            text = "\n".join(f"[{entry['start']:.1f}s] {entry['text'].strip()}" for entry in entries if entry.get("text"))
        else:
            text = " ".join(entry["text"].strip() for entry in entries if entry.get("text"))

        return [
            self._build_document(
                text,
                metadata={
                    "source_type": self.source_type.value,
                    "url": url,
                    "video_id": video_id,
                    "language": transcript.language_code,
                    "is_generated": transcript.is_generated,
                    "segment_count": len(entries),
                },
                source_id=video_id,
            )
        ]
    