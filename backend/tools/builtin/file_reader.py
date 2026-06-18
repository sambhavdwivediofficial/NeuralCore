# tools/builtin/file_reader.py
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from monitoring.logging import get_logger
from tools.schemas import ToolParameter, ToolParameterType, ToolSchema

logger = get_logger("neuralcore.tools.file_reader")

_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
_TEXT_EXTENSIONS = frozenset({
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bash",
    ".sql", ".html", ".css", ".scss", ".xml", ".csv", ".log", ".env",
    ".dockerfile", ".gitignore", ".editorconfig",
})

FILE_READER_SCHEMA = ToolSchema(
    name="file_reader",
    description=(
        "Read the contents of a file from the filesystem. "
        "Supports text files (returns raw content) and binary files (returns base64 encoded content). "
        "Maximum file size: 10 MB."
    ),
    parameters=[
        ToolParameter(name="file_path", type=ToolParameterType.STRING, description="Absolute or relative path to the file", required=True),
        ToolParameter(name="encoding", type=ToolParameterType.STRING, description="Text encoding for text files (default: utf-8)", required=False, default="utf-8"),
        ToolParameter(name="max_chars", type=ToolParameterType.INTEGER, description="Maximum characters to return for text files (0 = no limit, default: 50000)", required=False, default=50000),
        ToolParameter(name="start_line", type=ToolParameterType.INTEGER, description="Start line for partial reads (1-indexed, default: 1)", required=False, default=1),
        ToolParameter(name="end_line", type=ToolParameterType.INTEGER, description="End line for partial reads (0 = read all, default: 0)", required=False, default=0),
    ],
    returns="string content or base64 for binary files",
    category="filesystem",
)


async def file_reader_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    import asyncio

    file_path = Path(arguments["file_path"])
    encoding = arguments.get("encoding", "utf-8")
    max_chars = int(arguments.get("max_chars", 50000))
    start_line = max(1, int(arguments.get("start_line", 1)))
    end_line = int(arguments.get("end_line", 0))

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is a directory: {file_path}")

    stat = file_path.stat()
    if stat.st_size > _MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File too large: {stat.st_size / 1024 / 1024:.1f} MB (max 10 MB)")

    suffix = file_path.suffix.lower()
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    is_text = suffix in _TEXT_EXTENSIONS or (mime_type.startswith("text/"))

    if not is_text:
        raw = await asyncio.to_thread(file_path.read_bytes)
        return {
            "file_path": str(file_path),
            "size_bytes": stat.st_size,
            "mime_type": mime_type,
            "is_binary": True,
            "content_base64": base64.b64encode(raw).decode("utf-8"),
            "encoding": "base64",
        }

    raw_text = await asyncio.to_thread(file_path.read_text, encoding=encoding)
    lines = raw_text.splitlines()
    total_lines = len(lines)

    if start_line > 1 or end_line > 0:
        selected = lines[start_line - 1 : end_line if end_line > 0 else None]
        content = "\n".join(selected)
    else:
        content = raw_text

    if max_chars > 0 and len(content) > max_chars:
        content = content[:max_chars] + f"\n... [truncated at {max_chars} chars]"

    return {
        "file_path": str(file_path),
        "size_bytes": stat.st_size,
        "mime_type": mime_type,
        "is_binary": False,
        "content": content,
        "encoding": encoding,
        "total_lines": total_lines,
        "start_line": start_line,
        "end_line": end_line if end_line > 0 else total_lines,
        "char_count": len(content),
    }
