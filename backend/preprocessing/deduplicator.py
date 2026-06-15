# preprocessing/deduplicator.py
from __future__ import annotations

import hashlib
import re
from typing import Any

_TOKEN_PATTERN = re.compile(r"\w+")
_DEFAULT_SHINGLE_SIZE = 4
_DEFAULT_HASH_BITS = 64
_DEFAULT_HAMMING_THRESHOLD = 3


def compute_content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()


def _shingles(text: str, shingle_size: int = _DEFAULT_SHINGLE_SIZE) -> list[str]:
    tokens = _TOKEN_PATTERN.findall(text.lower())
    if len(tokens) < shingle_size:
        return [" ".join(tokens)] if tokens else []
    return [" ".join(tokens[i : i + shingle_size]) for i in range(len(tokens) - shingle_size + 1)]


def compute_simhash(text: str, hash_bits: int = _DEFAULT_HASH_BITS, shingle_size: int = _DEFAULT_SHINGLE_SIZE) -> int:
    shingles = _shingles(text, shingle_size)
    if not shingles:
        return 0

    weights = [0] * hash_bits
    byte_length = (hash_bits // 8) + 1
    for shingle in shingles:
        digest = hashlib.sha256(shingle.encode("utf-8")).digest()
        shingle_hash = int.from_bytes(digest[:byte_length], byteorder="big")
        for bit in range(hash_bits):
            if (shingle_hash >> bit) & 1:
                weights[bit] += 1
            else:
                weights[bit] -= 1

    fingerprint = 0
    for bit in range(hash_bits):
        if weights[bit] > 0:
            fingerprint |= (1 << bit)
    return fingerprint


def hamming_distance(first: int, second: int) -> int:
    return bin(first ^ second).count("1")


def deduplicate_documents(
    documents: list[dict[str, Any]],
    near_duplicate_threshold: int = _DEFAULT_HAMMING_THRESHOLD,
    hash_bits: int = _DEFAULT_HASH_BITS,
) -> list[dict[str, Any]]:
    unique_documents: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    seen_simhashes: list[int] = []

    for document in documents:
        text = document.get("text", "")
        if not text.strip():
            continue

        content_hash = compute_content_hash(text)
        if content_hash in seen_hashes:
            continue

        simhash = compute_simhash(text, hash_bits=hash_bits)
        if any(hamming_distance(simhash, existing) <= near_duplicate_threshold for existing in seen_simhashes):
            continue

        seen_hashes.add(content_hash)
        seen_simhashes.append(simhash)

        document_copy = dict(document)
        metadata = dict(document_copy.get("metadata", {}))
        metadata["content_hash"] = content_hash
        metadata["simhash"] = simhash
        document_copy["metadata"] = metadata
        unique_documents.append(document_copy)

    return unique_documents


def find_duplicate_groups(
    documents: list[dict[str, Any]],
    near_duplicate_threshold: int = _DEFAULT_HAMMING_THRESHOLD,
    hash_bits: int = _DEFAULT_HASH_BITS,
) -> list[list[int]]:
    fingerprints = [compute_simhash(document.get("text", ""), hash_bits=hash_bits) for document in documents]
    visited = [False] * len(documents)
    groups: list[list[int]] = []

    for i in range(len(documents)):
        if visited[i]:
            continue
        group = [i]
        visited[i] = True
        for j in range(i + 1, len(documents)):
            if visited[j]:
                continue
            if hamming_distance(fingerprints[i], fingerprints[j]) <= near_duplicate_threshold:
                group.append(j)
                visited[j] = True
        if len(group) > 1:
            groups.append(group)

    return groups
