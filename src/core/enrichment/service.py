from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

import structlog

from src.core.knowledge_registry.service import KnowledgeRegistry


logger = structlog.get_logger()

STOPWORDS: set[str] = {
    "a", "an", "the", "and", "or", "but", "in",
    "on", "at", "to", "for", "of", "with", "by",
    "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might",
    "shall", "can", "need", "dare", "ought", "used", "this",
    "that", "these", "those", "it", "its", "they", "them",
    "their", "we", "you", "he", "she", "who", "which",
    "what", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "some", "any", "no", "not",
    "so", "if", "then", "than", "too", "very", "just",
    "about", "up", "down", "out", "off", "over", "under",
    "again", "further", "once", "here", "there", "into", "onto",
    "upon", "within", "without", "also", "more", "most", "other",
    "such", "only", "own", "same", "because", "before", "after",
    "between", "through", "during", "since", "until", "while", "like",
    "although", "though", "whereas", "rather", "except", "even", "still",
    "yet", "already", "almost", "quite", "really", "well", "much",
    "many", "long", "able", "according", "across", "actually", "afterwards",
    "alone", "along", "always", "among", "amongst", "amount", "another",
    "anything", "anyway", "anywhere", "around", "back", "become", "becomes",
    "becoming", "beside", "besides", "beyond", "bottom", "call", "came",
    "cant", "cause", "certain", "clearly", "come", "couldnt", "de",
    "describe", "detail", "done", "due", "e.g", "eight", "either",
    "eleven", "else", "elsewhere", "empty", "enough", "etc", "ever",
    "everyone", "everything", "everywhere", "face", "fact", "fifteen", "fify",
    "fill", "find", "fire", "five", "former", "formerly", "found",
    "four", "front", "full", "get", "give", "go", "got",
    "group", "hence", "hereafter", "hereby", "herein", "hereupon", "herself",
    "himself", "hither", "however", "hundred", "indeed", "instead", "itself",
    "keep", "latter", "latterly", "least", "less", "lest", "made",
    "make", "making", "maybe", "mean", "meanwhile", "merely", "mine",
    "miss", "moreover", "mostly", "move", "myself", "namely", "neither",
    "nevertheless", "next", "nine", "nobody", "none", "nothing", "nowhere",
    "obtain", "often", "ourselves", "otherwise", "part", "per", "perhaps",
    "please", "poorly", "possible", "presumably", "previous", "previously", "promptly",
    "put", "readily", "regarding", "regardless", "regards", "result", "said",
    "seem", "seemed", "seeming", "seems", "serious", "several", "shed",
    "shes", "show", "showed", "shown", "shows", "side", "significant",
    "sincere", "six", "sixty", "somehow", "someone", "something", "sometime",
    "sometimes", "somewhere", "state", "strongly", "substantially", "successfully", "sufficiently",
    "tell", "ten", "th", "thee", "themselves", "thence", "thereafter",
    "thereby", "therefor", "therein", "thereupon", "thick", "thin", "third",
    "thorough", "thoroughly", "three", "throughout", "thru", "thus", "together",
    "top", "toward", "towards", "twelve", "twenty", "two", "un",
    "unless", "unlike", "unlikely", "us", "useful", "usefully", "usefulness",
    "using", "usually", "various", "via", "viz", "volume", "way",
    "yours", "yourself", "yourselves",
}

CONTENT_CLASS_PATTERNS: list[tuple[str, list[str]]] = [
    ("lesson", ["lesson", "objective", "learning outcome", "students will"]),
    ("assessment", ["assessment", "question", "answer", "multiple choice", "exam"]),
    ("lab_manual", ["procedure", "materials", "apparatus", "observation"]),
    ("reference", ["definition", "summary", "overview", "introduction"]),
    ("assignment", ["homework", "assignment", "exercise", "problem set"]),
    ("syllabus", ["syllabus", "course outline", "schedule", "week"]),
]


@dataclass
class EnrichmentResult:
    ko_id: str
    excerpt: str | None = None
    excerpt_source: str | None = None
    key_terms: list[str] = field(default_factory=list)
    content_class: str | None = None
    word_count: int = 0
    chunk_count: int = 0
    enrichment_version: str = "1"


class EnrichmentService:
    def __init__(
        self,
        registry: KnowledgeRegistry,
    ):
        self._registry = registry

    async def enrich(
        self,
        ko_id: str,
        chunks: list[str],
        content_type: str = "text/plain",
    ) -> EnrichmentResult:
        if not chunks:
            return EnrichmentResult(ko_id=ko_id, chunk_count=0, word_count=0)

        combined = self._join_chunks(chunks)
        word_count = len(combined.split())
        excerpt, excerpt_source = self._extract_excerpt(combined)
        key_terms = self._extract_key_terms(combined)
        content_class = self._classify_content(combined, content_type)

        result = EnrichmentResult(
            ko_id=ko_id,
            excerpt=excerpt,
            excerpt_source=excerpt_source,
            key_terms=key_terms,
            content_class=content_class,
            word_count=word_count,
            chunk_count=len(chunks),
            enrichment_version="1",
        )

        metadata = self._to_metadata(result)
        await self._registry.update_metadata(ko_id, metadata)

        logger.info(
            "enrichment_complete",
            ko_id=ko_id,
            word_count=word_count,
            key_term_count=len(key_terms),
            content_class=content_class,
        )
        return result

    def _join_chunks(self, chunks: list[str]) -> str:
        return "\n\n".join(chunks)

    def _extract_excerpt(self, text: str, max_chars: int = 500) -> tuple[str | None, str | None]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if len(cleaned) <= max_chars:
            return cleaned, "full_text"
        first_para = text.split("\n\n")[0].strip()
        cleaned_first = re.sub(r"\s+", " ", first_para)
        if len(cleaned_first) <= max_chars:
            return cleaned_first, "first_paragraph"
        return cleaned[:max_chars].rsplit(" ", 1)[0] + "...", "truncated"

    def _extract_key_terms(
        self, text: str, max_terms: int = 20, min_length: int = 3, min_freq: int = 2
    ) -> list[str]:
        cleaned = re.sub(r"[^a-zA-Z\s]", " ", text.lower())
        tokens = cleaned.split()
        tokens = [t for t in tokens if len(t) >= min_length and t not in STOPWORDS]
        freq: dict[str, int] = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1
        sorted_terms = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
        return [term for term, count in sorted_terms[:max_terms] if count >= min_freq]

    def _classify_content(self, text: str, content_type: str) -> str | None:
        lower = text.lower()
        for class_name, patterns in CONTENT_CLASS_PATTERNS:
            if any(p in lower for p in patterns):
                return class_name
        if content_type == "application/pdf":
            return "document"
        if content_type.startswith("text/"):
            return "text"
        return None

    def _to_metadata(self, result: EnrichmentResult) -> dict:
        return {"enrichment": json.dumps(asdict(result))}
