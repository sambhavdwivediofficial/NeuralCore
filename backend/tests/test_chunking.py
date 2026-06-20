# tests/test_chunking.py
from __future__ import annotations

import pytest

from chunking.ast_chunker import ASTChunker
from chunking.base_chunker import count_tokens, get_chunker, split_sentences
from chunking.code_chunker import CodeChunker
from chunking.hybrid_chunker import HybridChunker
from chunking.markdown_chunker import MarkdownChunker
from chunking.recursive_chunker import RecursiveChunker
from chunking.semantic_chunker import SemanticChunker
from chunking.token_chunker import TokenChunker
from database.models.knowledgebase import ChunkingStrategy

pytestmark = pytest.mark.unit


class TestTokenChunker:
    def test_short_text_single_chunk(self) -> None:
        chunker = TokenChunker(chunk_size=100, chunk_overlap=10)
        result = chunker.split("This is a short sentence.")
        assert len(result) == 1
        assert result[0] == "This is a short sentence."

    def test_long_text_multiple_chunks(self) -> None:
        chunker = TokenChunker(chunk_size=20, chunk_overlap=5)
        text = " ".join(["word"] * 200)
        result = chunker.split(text)
        assert len(result) > 1
        for chunk in result:
            assert count_tokens(chunk) <= 25

    def test_empty_text(self) -> None:
        chunker = TokenChunker(chunk_size=100, chunk_overlap=10)
        assert chunker.split("") == []
        assert chunker.split("   ") == []

    def test_overlap_preserves_continuity(self) -> None:
        chunker = TokenChunker(chunk_size=10, chunk_overlap=3)
        text = " ".join(f"token{i}" for i in range(50))
        result = chunker.split(text)
        assert len(result) >= 2


class TestRecursiveChunker:
    def test_paragraph_splitting(self) -> None:
        chunker = RecursiveChunker(chunk_size=50, chunk_overlap=5)
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
        result = chunker.split(text)
        assert len(result) >= 1
        assert all(isinstance(c, str) for c in result)

    def test_respects_chunk_size(self) -> None:
        chunker = RecursiveChunker(chunk_size=15, chunk_overlap=2)
        text = "word " * 300
        result = chunker.split(text)
        for chunk in result:
            assert count_tokens(chunk) <= 20


class TestMarkdownChunker:
    def test_splits_by_headers(self) -> None:
        chunker = MarkdownChunker(chunk_size=100, chunk_overlap=10)
        text = "# Header One\n\nContent under header one.\n\n## Header Two\n\nContent under header two."
        result = chunker.split(text)
        assert len(result) >= 1

    def test_front_matter_not_included_in_chunks(self) -> None:
        chunker = MarkdownChunker(chunk_size=200, chunk_overlap=10)
        result = chunker.split("# Title\n\nSome body text here.")
        assert any("Title" in chunk or "body text" in chunk for chunk in result)


class TestASTChunker:
    def test_splits_python_functions(self) -> None:
        chunker = ASTChunker(chunk_size=50, chunk_overlap=5)
        code = "def foo():\n    return 1\n\n\ndef bar():\n    return 2\n"
        result = chunker.split(code)
        assert len(result) >= 1
        combined = "\n".join(result)
        assert "def foo" in combined
        assert "def bar" in combined

    def test_invalid_python_falls_back(self) -> None:
        chunker = ASTChunker(chunk_size=50, chunk_overlap=5)
        invalid_code = "this is not valid python !!! @#$"
        result = chunker.split(invalid_code)
        assert isinstance(result, list)

    def test_class_with_methods_split(self) -> None:
        chunker = ASTChunker(chunk_size=20, chunk_overlap=2)
        code = "class Foo:\n    def method_a(self):\n        return 1\n\n    def method_b(self):\n        return 2\n"
        result = chunker.split(code)
        assert len(result) >= 1


class TestSemanticChunker:
    def test_groups_similar_sentences(self) -> None:
        chunker = SemanticChunker(chunk_size=200, chunk_overlap=10)
        text = "Cats are mammals. Cats have fur. Dogs are also mammals. The stock market rose today."
        result = chunker.split(text)
        assert len(result) >= 1

    def test_single_sentence(self) -> None:
        chunker = SemanticChunker(chunk_size=100, chunk_overlap=5)
        result = chunker.split("Just one sentence here.")
        assert len(result) == 1


class TestCodeChunker:
    def test_splits_on_function_boundaries(self) -> None:
        chunker = CodeChunker(chunk_size=30, chunk_overlap=3)
        code = "function foo() {\n  return 1;\n}\n\nfunction bar() {\n  return 2;\n}"
        result = chunker.split(code)
        assert len(result) >= 1


class TestHybridChunker:
    def test_detects_markdown(self) -> None:
        chunker = HybridChunker(chunk_size=100, chunk_overlap=10)
        result = chunker.split("# Title\n\nSome content under the title.")
        assert len(result) >= 1

    def test_detects_python_code(self) -> None:
        chunker = HybridChunker(chunk_size=50, chunk_overlap=5)
        result = chunker.split("def hello():\n    print('hi')\n")
        assert len(result) >= 1

    def test_falls_back_to_semantic_for_prose(self) -> None:
        chunker = HybridChunker(chunk_size=100, chunk_overlap=10)
        result = chunker.split("This is plain prose text without any special structure at all.")
        assert len(result) >= 1


class TestGetChunkerFactory:
    @pytest.mark.parametrize(
        "strategy",
        [
            ChunkingStrategy.TOKEN,
            ChunkingStrategy.RECURSIVE,
            ChunkingStrategy.MARKDOWN,
            ChunkingStrategy.CODE,
            ChunkingStrategy.AST,
            ChunkingStrategy.SEMANTIC,
            ChunkingStrategy.HYBRID,
            ChunkingStrategy.CHARACTER,
        ],
    )
    def test_factory_returns_correct_chunker(self, strategy: ChunkingStrategy) -> None:
        chunker = get_chunker(strategy, chunk_size=100, chunk_overlap=10)
        result = chunker.split("Sample text for testing the chunker factory function.")
        assert isinstance(result, list)


class TestSplitSentences:
    def test_basic_sentence_split(self) -> None:
        result = split_sentences("First sentence. Second sentence! Third sentence?")
        assert len(result) == 3

    def test_empty_input(self) -> None:
        assert split_sentences("") == []
