"""Evidence deduplication for Agentic RAG.

Filters out exact duplicates (by content hash) and semantic near-duplicates
(by token overlap) before persisting evidence records.
"""

import hashlib
import re

# Stopwords for semantic dedup tokenization
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "can", "may", "might", "shall",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "not", "only", "own",
    "same", "so", "than", "too", "very", "it", "its", "this",
    "that", "these", "those",
}


def compute_content_hash(content: str) -> str:
    """Compute a SHA-256 hash of the content for exact dedup."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def is_semantic_duplicate(
    content: str,
    existing_contents: list[str],
    threshold: float = 0.75,
) -> bool:
    """Check if content is a semantic near-duplicate of any existing content.

    Uses token overlap (Jaccard-like) ratio. Content is considered a
    duplicate when it shares ≥threshold of its tokens with any existing
    content.

    Args:
        content: New content to check.
        existing_contents: Already-stored content strings.
        threshold: Overlap ratio at which content is considered duplicate.

    Returns:
        True if content is a semantic duplicate.
    """
    if not existing_contents:
        return False

    tokens = _tokenize(content)
    if not tokens:
        return False

    for existing in existing_contents:
        existing_tokens = _tokenize(existing)
        if not existing_tokens:
            continue
        overlap = tokens & existing_tokens
        ratio = len(overlap) / len(tokens)
        if ratio >= threshold:
            return True

    return False


def filter_duplicates(
    chunks: list[dict],
    existing_contents: list[str] | None = None,
    existing_hashes: set[str] | None = None,
    semantic_threshold: float = 0.75,
) -> list[dict]:
    """Filter out exact and semantic duplicate chunks.

    Checks both content hash (exact) and token overlap (semantic).
    Preserves the first occurrence of each unique chunk.

    Args:
        chunks: List of chunk dicts, each with a 'content' field.
        existing_contents: Contents already persisted (for cross-batch dedup).
        existing_hashes: Content hashes already persisted.
        semantic_threshold: Overlap ratio for semantic dedup.

    Returns:
        Filtered list with duplicates removed.
    """
    seen_hashes: set[str] = set(existing_hashes or [])
    seen_contents: list[str] = list(existing_contents or [])
    filtered: list[dict] = []

    for chunk in chunks:
        content = chunk.get("content", "")
        if not content:
            continue

        h = compute_content_hash(content)
        if h in seen_hashes:
            continue

        if is_semantic_duplicate(content, seen_contents, semantic_threshold):
            continue

        seen_hashes.add(h)
        seen_contents.append(content)
        filtered.append(chunk)

    return filtered
