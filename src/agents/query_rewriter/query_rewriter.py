"""Query Rewriter Agent for Agentic RAG.

Transforms user queries and plan subtasks into source-aware,
retrieval-oriented query bundles.

Implements PRD-003: Query Rewriter Agent.
"""

import json
import logging

from src.agents.base import BaseAgent
from src.agents.query_rewriter.models import QueryBundle, QueryCategory, RewrittenQuery
from src.agents.query_rewriter.prompts import REWRITER_SYSTEM_PROMPT, build_rewriter_prompt

logger = logging.getLogger(__name__)

MAX_QUERIES = 7
FALLBACK_COVERAGE = 0.5

FALLBACK_BUNDLE = QueryBundle(
    original_query="",
    rewritten_queries=[
        RewrittenQuery(
            query="{original_query}",
            source_type="curriculum",
            purpose="Fallback single query",
            priority=5,
        ),
    ],
    estimated_coverage=FALLBACK_COVERAGE,
)


class QueryRewriterAgent(BaseAgent):
    """Agent that rewrites user queries into retrieval-oriented query bundles.

    Converts high-level user requests and planner subtasks into
    multiple source-aware queries for better retrieval coverage.
    Supports curriculum, memory, misconception, learner_profile,
    recommendation, comparison, and definition query categories.
    """

    def __init__(self, llm_router):
        super().__init__(llm_router, name="query_rewriter")

    async def rewrite(
        self,
        user_query: str,
        subtasks: list[dict] | None = None,
        learner_snapshot: dict | None = None,
    ) -> QueryBundle:
        """Generate a source-aware query bundle from a user request.

        Args:
            user_query: The original user question or request.
            subtasks: Optional plan subtasks guiding query decomposition.
            learner_snapshot: Optional learner data for personalization.

        Returns:
            QueryBundle with rewritten queries and coverage estimate.
        """
        user_prompt = build_rewriter_prompt(user_query, subtasks, learner_snapshot)

        try:
            result = await self._call_llm(
                system_prompt=REWRITER_SYSTEM_PROMPT,
                user_message=user_prompt,
                temperature=0.3,
                max_tokens=2048,
                request_type="query_rewrite",
            )

            content = result["content"]
            bundle = self._parse_bundle(content, user_query, subtasks)
            return bundle

        except Exception as e:
            logger.warning("query_rewrite_failed: %s", str(e))
            return self._build_fallback(user_query, subtasks)

    def _parse_bundle(
        self, content: str, original_query: str, subtasks: list[dict] | None = None
    ) -> QueryBundle:
        """Parse LLM response into a QueryBundle.

        Handles markdown code blocks and partial parsing.
        Falls back to heuristic on parse failure.
        """
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("query_rewrite_parse_failed, using fallback")
            return self._build_fallback(original_query)

        raw_queries = parsed.get("queries", [])
        rewritten = []
        for q in raw_queries[:MAX_QUERIES]:
            rewritten.append(
                RewrittenQuery(
                    query=q.get("query", ""),
                    source_type=self._validate_category(q.get("category", "curriculum")),
                    purpose=q.get("purpose", ""),
                    priority=int(q.get("priority", 5)),
                )
            )

        coverage = float(parsed.get("coverage_score", FALLBACK_COVERAGE))
        coverage = max(0.0, min(1.0, coverage))

        heuristic_coverage = self._calculate_heuristic_coverage(
            rewritten, subtasks
        )
        if heuristic_coverage is not None:
            coverage = min(coverage, heuristic_coverage)

        return QueryBundle(
            original_query=original_query,
            rewritten_queries=rewritten,
            estimated_coverage=coverage,
        )

    def _validate_category(self, category: str) -> str:
        """Ensure category is one of the valid QueryCategory values."""
        try:
            return QueryCategory(category).value
        except ValueError:
            return QueryCategory.CURRICULUM.value

    def _calculate_heuristic_coverage(
        self,
        rewritten_queries: list[RewrittenQuery],
        subtasks: list[dict] | None,
    ) -> float | None:
        """Calculate coverage by checking subtask type coverage.

        Returns adjusted score (0.0-1.0), or None if no subtasks to check.
        """
        if not subtasks:
            return None

        requested_types = {st.get("type", "curriculum") for st in subtasks if st.get("objective")}
        covered_types = {rq.source_type for rq in rewritten_queries}

        if not requested_types:
            return None

        covered = requested_types & covered_types
        ratio = len(covered) / len(requested_types)
        return max(0.1, ratio)

    def _build_fallback(
        self,
        user_query: str,
        subtasks: list[dict] | None = None,
    ) -> QueryBundle:
        """Build a heuristic fallback bundle when LLM fails.

        Decomposes subtasks into individual queries, or falls back
        to a single-query bundle.
        """
        queries: list[RewrittenQuery] = []

        if subtasks:
            for i, st in enumerate(subtasks):
                objective = st.get("objective", st.get("description", ""))
                if not objective:
                    continue
                stype = st.get("type", "curriculum")
                queries.append(
                    RewrittenQuery(
                        query=objective,
                        source_type=self._validate_category(stype),
                        purpose=f"Subtask {i + 1} decomposition",
                        priority=max(1, 10 - i),
                    )
                )

        if not queries:
            queries.append(
                RewrittenQuery(
                    query=user_query,
                    source_type="curriculum",
                    purpose="Fallback: original query",
                    priority=5,
                )
            )

        return QueryBundle(
            original_query=user_query,
            rewritten_queries=queries,
            estimated_coverage=0.4,
        )

    def group_by_source(self, bundle: QueryBundle) -> dict[str, list[str]]:
        """Group rewritten queries by their source_type category.

        Returns:
            Dict mapping source_type to list of query strings.
        """
        groups: dict[str, list[str]] = {}
        for rq in bundle.rewritten_queries:
            cat = rq.source_type
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(rq.query)
        return groups
