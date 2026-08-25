"""Tests for multi-subject support: ingestion layout, retrieval filters, metadata defaults.

Legacy chunks/files predate the `subject` field and are treated as biology.
"""

import os

from scripts.ingest_curriculum import (
    detect_subject_from_path,
    scan_files,
)
from src.rag.pgvector_store import _parse_metadata
from src.retrieval.adapter import RetrievalFilter
from src.retrieval.bm25 import BM25Index


class TestDetectSubjectFromPath:
    def test_canonical_layout_extracts_subject(self, tmp_path):
        fp = tmp_path / "Chemistry" / "Grade10" / "chem.pdf"
        assert detect_subject_from_path(str(fp), str(tmp_path)) == "chemistry"

    def test_legacy_layout_defaults_to_biology(self, tmp_path):
        fp = tmp_path / "Grade10" / "bio.pdf"
        assert detect_subject_from_path(str(fp), str(tmp_path)) == "biology"

    def test_subject_normalized_lowercase(self, tmp_path):
        fp = tmp_path / "Physics" / "Grade9" / "phys.pdf"
        assert detect_subject_from_path(str(fp), str(tmp_path)) == "physics"


class TestScanFiles:
    def _touch(self, *parts):
        path = os.path.join(*parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("x")

    def test_scans_both_layouts_with_subjects(self, tmp_path):
        base = str(tmp_path)
        self._touch(base, "Chemistry", "Grade10", "chem.pdf")
        self._touch(base, "Biology", "Grade9", "bio.pdf")
        self._touch(base, "Grade11", "legacy.pdf")

        files = scan_files(base)
        by_name = {f["filename"]: f for f in files}

        assert by_name["chem.pdf"]["subject"] == "chemistry"
        assert by_name["bio.pdf"]["subject"] == "biology"
        assert by_name["legacy.pdf"]["subject"] == "biology"

    def test_no_duplicate_paths_across_layouts(self, tmp_path):
        base = str(tmp_path)
        self._touch(base, "Grade10", "bio.pdf")
        files = scan_files(base)
        assert len(files) == 1
        assert files[0]["filepath"].endswith("bio.pdf")

    def test_ignores_non_curriculum_dirs(self, tmp_path):
        base = str(tmp_path)
        self._touch(base, "random_dir", "file.pdf")
        assert scan_files(base) == []


class TestRetrievalFilterSubject:
    def test_subject_included_in_where(self):
        f = RetrievalFilter(grade_level=10, subject="Chemistry")
        assert f.subject == "chemistry"
        where = f.to_chroma_where()
        assert {"subject": {"$eq": "chemistry"}} in where["$and"]

    def test_none_subject_omitted_from_where(self):
        f = RetrievalFilter(grade_level=10)
        where = f.to_chroma_where()
        assert "subject" not in str(where)


class TestBM25SubjectFilter:
    def _index_with(self, metadatas, tmp_path):
        idx = BM25Index(persist_path=str(tmp_path / "bm25_test.pkl"))
        idx.build(
            documents=["photosynthesis converts light energy",
                       "stoichiometry balances chemical equations"],
            ids=["doc1", "doc2"],
            metadatas=metadatas,
        )
        return idx

    def test_subject_filter_matches_tagged_docs(self, tmp_path):
        idx = self._index_with(
            [{"subject": "biology"}, {"subject": "chemistry"}], tmp_path
        )
        results = idx.search("energy equations", n_results=5, subject="chemistry")
        assert [r["doc_id"] for r in results] == ["doc2"]

    def test_untagged_metadata_treated_as_biology(self, tmp_path):
        idx = self._index_with([{}, {"subject": "chemistry"}], tmp_path)
        results = idx.search("light energy", n_results=5, subject="biology")
        assert [r["doc_id"] for r in results] == ["doc1"]

    def test_no_subject_filter_returns_all(self, tmp_path):
        idx = self._index_with([{}, {"subject": "chemistry"}], tmp_path)
        results = idx.search("energy", n_results=5)
        assert len(results) == 2


class TestPgvectorMetadataDefault:
    def test_missing_subject_defaults_to_biology(self):
        meta = _parse_metadata('{"grade_level": 10}')
        assert meta["subject"] == "biology"

    def test_explicit_subject_preserved(self):
        meta = _parse_metadata('{"grade_level": 10, "subject": "physics"}')
        assert meta["subject"] == "physics"

    def test_dict_input_gets_default_without_mutation(self):
        raw = {"grade_level": 9}
        meta = _parse_metadata(raw)
        assert meta["subject"] == "biology"
        assert "subject" not in raw
