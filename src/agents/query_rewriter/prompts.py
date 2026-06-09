"""System prompts for the Query Rewriter Agent.

Implements the PRD-003 prompt design with retrieval-oriented instructions.
"""

REWRITER_SYSTEM_PROMPT = """You are the Query Rewriter Agent for EthioBio.

Your responsibility is to transform a retrieval plan into optimized search queries.

Create focused, atomic, retrieval-oriented queries.

Do not answer the question.
Do not retrieve documents.
Only generate search queries.

## Query Categories

Every generated query must belong to one of these categories:
- "curriculum": Textbook content, course material definitions
- "memory": Past interactions, session history
- "misconception": Known student misconceptions
- "learner_profile": Student mastery, abilities, readiness
- "recommendation": Study recommendations
- "comparison": Side-by-side concept comparison
- "definition": Term or concept definitions

## Query Quality Rules

All queries must:

### Be Atomic
Good: "meiosis stages"
Bad: "Explain all details about meiosis and compare it with mitosis and tell me what I got wrong"

### Be Search-Oriented
Good: "cell division misconceptions"
Bad: "Could you please tell me why students usually make mistakes?"

### Be Source-Specific
Each query must clearly target a retrieval domain via its category.

## Expansion Rules

### Definition queries expand into:
- definition
- key concepts
- examples

### Comparison queries expand into:
- concept A alone
- concept B alone
- differences between A and B
- similarities between A and B

### Personalized queries expand into:
- topic misconceptions
- topic learner history
- previous topic questions
- topic readiness

## Output Format

Respond with a JSON object matching this schema:
{
  "queries": [
    {
      "query": "meiosis stages",
      "category": "curriculum",
      "purpose": "Retrieve meiosis stage descriptions",
      "priority": 8
    }
  ],
  "coverage_score": 0.85,
  "missing_topics": []
}
"""


def build_rewriter_prompt(
    user_query: str,
    subtasks: list[dict] | None = None,
    learner_snapshot: dict | None = None,
) -> str:
    """Build the user prompt for the Query Rewriter Agent.

    Args:
        user_query: The user's original question.
        subtasks: Optional list of plan subtasks to decompose into queries.
        learner_snapshot: Optional learner data for personalization.

    Returns:
        Formatted user prompt string.
    """
    parts = [f"Original Query: {user_query}"]

    if subtasks:
        parts.append("\nPlan Subtasks:")
        for i, st in enumerate(subtasks):
            obj = st.get("objective", st.get("description", ""))
            stype = st.get("type", "curriculum")
            parts.append(f"{i + 1}. [{stype}] {obj}")

    if learner_snapshot:
        weak = learner_snapshot.get("weak_topics", [])
        misconceptions = learner_snapshot.get("misconceptions", [])
        mastery = learner_snapshot.get("mastery_by_topic", {})

        ctx = []
        if weak:
            ctx.append(f"Weak topics: {', '.join(weak)}")
        if misconceptions:
            ctx.append(f"Active misconceptions: {len(misconceptions)}")
        if mastery:
            low = [
                f"{t}({s:.0f}%)"
                for t, s in mastery.items()
                if isinstance(s, (int, float)) and s < 60
            ]
            if low:
                ctx.append(f"Low mastery: {', '.join(low)}")

        if ctx:
            parts.append("\nLearner Context:\n" + "\n".join(ctx))

    parts.append(
        "\n\nGenerate 3-7 retrieval-oriented queries covering all topics and categories needed. "
        "Set coverage_score based on how well the generated queries cover the original request."
    )

    return "\n".join(parts)
