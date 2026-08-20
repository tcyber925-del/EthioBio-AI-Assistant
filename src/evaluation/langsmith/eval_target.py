"""Target function for LangSmith evaluate() — a thin wrapper over run_graph."""


async def eval_target(inputs: dict) -> dict:
    """Run the full Agentic RAG pipeline on a dataset example.

    inputs: {"question", "grade_level", "language"} — matches the dataset
    schema produced by sync_datasets.
    """
    from src.graph.orchestrator import run_graph

    result = await run_graph(
        user_message=inputs["question"],
        grade_level=inputs.get("grade_level"),
        language=inputs.get("language", "en"),
    )
    return {
        "answer": result.answer,
        "sources": result.sources,
        "context": "\n".join(result.sources),
    }
