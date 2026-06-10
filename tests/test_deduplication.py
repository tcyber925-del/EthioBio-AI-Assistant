"""Tests for evidence deduplication."""
from src.core.evidence.deduplication import (
    compute_content_hash,
    filter_duplicates,
    is_semantic_duplicate,
)


class TestContentHash:
    def test_hash_is_deterministic(self):
        h1 = compute_content_hash("Cell theory")
        h2 = compute_content_hash("Cell theory")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = compute_content_hash("Cell theory")
        h2 = compute_content_hash("Mitosis")
        assert h1 != h2

    def test_hash_is_sha256_hex(self):
        h = compute_content_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestSemanticDuplicate:
    def test_exact_match_is_duplicate(self):
        assert is_semantic_duplicate(
            "Mitosis is cell division",
            ["Mitosis is cell division"],
        )

    def test_high_overlap_is_duplicate(self):
        assert is_semantic_duplicate(
            "Mitosis is the process of cell division",
            ["Mitosis is cell division"],
        )

    def test_low_overlap_not_duplicate(self):
        assert not is_semantic_duplicate(
            "Photosynthesis occurs in chloroplasts",
            ["Mitosis is the process of cell division"],
        )

    def test_empty_content_not_duplicate(self):
        assert not is_semantic_duplicate("", ["some content"])

    def test_no_existing_not_duplicate(self):
        assert not is_semantic_duplicate("test", [])

    def test_empty_existing_not_duplicate(self):
        assert not is_semantic_duplicate("test", [""])


class TestFilterDuplicates:
    def test_no_duplicates(self):
        chunks = [
            {"content": "Cell theory", "score": 0.9},
            {"content": "Mitosis is cell division", "score": 0.8},
        ]
        result = filter_duplicates(chunks)
        assert len(result) == 2

    def test_exact_duplicate_removed(self):
        chunks = [
            {"content": "Cell theory", "score": 0.9},
            {"content": "Cell theory", "score": 0.8},
        ]
        result = filter_duplicates(chunks)
        assert len(result) == 1

    def test_semantic_duplicate_removed(self):
        chunks = [
            {"content": "Mitosis is the process of cell division", "score": 0.9},
            {"content": "Mitosis is cell division", "score": 0.8},
        ]
        result = filter_duplicates(chunks)
        assert len(result) == 1

    def test_respects_existing_hashes(self):
        chunks = [
            {"content": "Cell theory", "score": 0.9},
        ]
        result = filter_duplicates(
            chunks,
            existing_hashes={compute_content_hash("Cell theory")},
        )
        assert len(result) == 0

    def test_respects_existing_contents(self):
        chunks = [
            {"content": "Mitosis is cell division", "score": 0.9},
        ]
        result = filter_duplicates(
            chunks,
            existing_contents=["Mitosis is the process of cell division"],
        )
        assert len(result) == 0

    def test_empty_chunks(self):
        assert filter_duplicates([]) == []

    def test_skips_empty_content(self):
        chunks = [{"content": ""}]
        result = filter_duplicates(chunks)
        assert len(result) == 0
