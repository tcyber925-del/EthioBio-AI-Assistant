"""Retrieval node — fetches curriculum context from vector store."""

import re

from src.graph.state import AgentState
from src.retrieval.adapter import RetrievalFilter, RetrievalResult, VectorStoreAdapter
from src.schemas.streaming import TokenChunk

N_RESULTS = 8

# Front-matter offset: PDF page number - textbook page number per grade
# Each textbook PDF has N front-matter pages (cover, copyright, TOC) before
# the printed textbook page 1 begins. Subtract this offset when displaying.
PAGE_OFFSET = {9: 7, 10: 6, 11: 10, 12: 5}


def _correct_page(page_number: int, grade_level: int) -> int:
    offset = PAGE_OFFSET.get(grade_level, 0)
    return max(1, page_number - offset)


def _is_quality_content(text: str) -> bool:
    """Check if text has usable body content (not just headings/figure captions)."""
    if not text or len(text) < 100:
        return False
    alpha = sum(1 for c in text if c.isalpha())
    if (alpha / len(text)) < 0.55:
        return False
    for c in text:
        cp = ord(c)
        if cp < 0x20 and cp not in (0x09, 0x0A, 0x0C, 0x0D):
            return False
        if 0x7F <= cp <= 0x9F:
            return False
    # Must contain a complete sentence with subject + verb + period
    has_sentence = bool(
        re.search(
            r"[A-Z][a-z]+(?: is| are| has| have| can| will| does| do| was| were| refers| contains| involves| produces| consists)[\s\w,.]+\.",
            text,
            re.IGNORECASE,
        )
    )
    # OR at least 80 consecutive non-whitespace characters (body text block)
    stripped = re.sub(r"\s+", "", text)
    has_text_block = len(stripped) > 80
    return has_sentence or has_text_block


    def _push_status(self, state: AgentState, message: str):
        if state.token_queue:
            state.token_queue.put_nowait(TokenChunk(delta=message, node="retrieve", status=True))


class RetrievalNode:
    def __init__(self, adapter: VectorStoreAdapter):
        self.adapter = adapter

    async def __call__(self, state: AgentState) -> AgentState:
        query = state.user_message
        if state.retrieval_query:
            query = state.retrieval_query

        self._push_status(state, "Searching your grade level...")

        # Search pipeline: exact grade → neighboring grades → no filter
        search_rounds = []

        # Round 1: exact grade
        filter_obj = RetrievalFilter(grade_level=state.grade_level)
        r1 = await self.adapter.search(query, n_results=N_RESULTS, filter_obj=filter_obj)
        search_rounds.append((r1, "exact"))

        # Round 2: nearest neighboring grades only (±1, not ±2)
        if state.grade_level:
            for offset in [1, -1]:
                adj_grade = state.grade_level + offset
                if adj_grade < 7 or adj_grade > 12:
                    continue
                self._push_status(state, f"Checking Grade {adj_grade} materials...")
                adj_filter = RetrievalFilter(grade_level=adj_grade)
                adj_results = await self.adapter.search(
                    query, n_results=N_RESULTS, filter_obj=adj_filter
                )
                search_rounds.append((adj_results, f"grade_{adj_grade}"))

        # Aggregate results from first two rounds
        all_raw = []
        for results, _tag in search_rounds:
            all_raw.extend(results)

        # Round 3: no filter (only if we still need more)
        if len(set(r.content[:80] for r in all_raw)) < 6:
            self._push_status(state, "Searching broader curriculum...")
            fallback = await self.adapter.search(
                query, n_results=N_RESULTS, filter_obj=RetrievalFilter()
            )
            all_raw.extend(fallback)

        # Deduplicate before quality filter
        seen_ids = set()
        deduped_raw = []
        for r in all_raw:
            key = r.content[:120]
            if key not in seen_ids:
                seen_ids.add(key)
                deduped_raw.append(r)

        # Quality filter
        quality_results = [r for r in deduped_raw if _is_quality_content(r.content)]

        # Fallback: if no quality content, use min threshold
        if not quality_results:
            quality_results = deduped_raw[:2]

        # Sort by relevance score so best content fits in format_context's 4000-char budget
        quality_results.sort(key=lambda r: r.score, reverse=True)

        # Correct page numbers for front-matter offset and build final output
        corrected_results = []
        for r in quality_results:
            meta = dict(r.metadata)
            grade = meta.get("grade_level", 0)
            if "page_number" in meta:
                meta["page_number"] = _correct_page(meta["page_number"], grade)
            corrected_results.append(
                RetrievalResult(
                    content=r.content,
                    metadata=meta,
                    score=r.score,
                    source_id=r.source_id,
                )
            )

        state.retrieved_chunks = [
            {
                "content": r.content,
                "metadata": r.metadata,
                "score": r.score,
                "source_id": r.source_id,
            }
            for r in corrected_results
        ]
        state.context = self.adapter.format_context(corrected_results)

        return state


class SkipRetrievalNode:
    def __init__(self, adapter: VectorStoreAdapter = None):
        self.adapter = adapter

    async def __call__(self, state: AgentState) -> AgentState:
        state.retrieved_chunks = []
        state.context = ""
        return state
