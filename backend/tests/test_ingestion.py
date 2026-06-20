# tests/test_ingestion.py
from __future__ import annotations

import asyncio

import pytest

from ingestion.base_loader import SourceType, UnsupportedSourceError
from ingestion.loader_factory import get_loader
from preprocessing.deduplicator import deduplicate_documents
from settings import get_settings

pytestmark = pytest.mark.unit


class TestLoaderFactory:
    def test_get_txt_loader(self) -> None:
        settings = get_settings()
        loader = get_loader("txt", settings)
        assert loader.source_type == SourceType.TXT

    def test_get_pdf_loader(self) -> None:
        settings = get_settings()
        loader = get_loader("pdf", settings)
        assert loader.source_type == SourceType.PDF

    def test_unsupported_loader_raises(self) -> None:
        settings = get_settings()
        with pytest.raises(ValueError):
            get_loader("nonexistent_source_type", settings)

    @pytest.mark.parametrize(
        "source_type",
        ["txt", "markdown", "html", "csv", "json", "xml", "xlsx", "docx", "pdf"],
    )
    def test_all_file_loaders_load_successfully(self, source_type: str) -> None:
        settings = get_settings()
        loader = get_loader(source_type, settings)
        assert loader.source_type.value == source_type


class TestTxtLoader:
    @pytest.mark.asyncio
    async def test_load_from_content(self) -> None:
        settings = get_settings()
        loader = get_loader("txt", settings)
        result = await loader.load({"content": "Hello NeuralCore"})
        assert len(result) == 1
        assert result[0]["text"] == "Hello NeuralCore"
        assert result[0]["metadata"]["source_type"] == "txt"


class TestMarkdownLoader:
    @pytest.mark.asyncio
    async def test_extracts_front_matter(self) -> None:
        settings = get_settings()
        loader = get_loader("markdown", settings)
        content = "---\ntitle: Test Doc\nauthor: Sambhav\n---\n\nBody content here."
        result = await loader.load({"content": content})
        assert len(result) == 1
        assert result[0]["metadata"].get("title") == "Test Doc"
        assert "Body content here" in result[0]["text"]


class TestJsonLoader:
    @pytest.mark.asyncio
    async def test_load_list_of_records(self) -> None:
        settings = get_settings()
        loader = get_loader("json", settings)
        result = await loader.load({"content": '[{"name": "item1"}, {"name": "item2"}]'})
        assert len(result) == 2


class TestCsvLoader:
    @pytest.mark.asyncio
    async def test_load_per_row(self) -> None:
        settings = get_settings()
        loader = get_loader("csv", settings)
        content = "name,age\nAlice,30\nBob,25"
        result = await loader.load({"content": content})
        assert len(result) == 2
        assert "Alice" in result[0]["text"]


class TestDeduplicator:
    def test_removes_exact_duplicates(self, sample_documents) -> None:
        docs_with_dupe = sample_documents + [dict(sample_documents[0])]
        deduplicated = deduplicate_documents(docs_with_dupe)
        assert len(deduplicated) == len(sample_documents)

    def test_preserves_unique_documents(self, sample_documents) -> None:
        deduplicated = deduplicate_documents(sample_documents)
        assert len(deduplicated) == 3

    def test_empty_list(self) -> None:
        assert deduplicate_documents([]) == []
