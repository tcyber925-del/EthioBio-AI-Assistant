"""
Ragas evaluation test suite for RAG quality.

Measures:
- Faithfulness: Is the answer grounded in the retrieved context?
- Answer Relevancy: Does the answer address the question?
- Context Recall: Was all relevant context retrieved?
- Context Precision: Was the retrieved context relevant?

Usage:
    python -m src.evaluation.ragas_test
"""

import json
import os
from typing import Optional

GOLD_SET_PATH = os.path.join(os.path.dirname(__file__), "gold_set.json")


def load_gold_set() -> list[dict]:
    if os.path.exists(GOLD_SET_PATH):
        with open(GOLD_SET_PATH) as f:
            return json.load(f)
    return _default_gold_set()


def _default_gold_set() -> list[dict]:
    return [
        {
            "id": "tutor-cell-theory",
            "type": "tutor",
            "question": "What is cell theory?",
            "expected_answer": "Cell theory states that all living organisms are composed of cells, the cell is the basic unit of life, and all cells arise from pre-existing cells.",
            "grade_level": 9,
            "topic": "Cell Biology",
            "language": "en",
        },
        {
            "id": "tutor-mitosis",
            "type": "tutor",
            "question": "Explain the process of mitosis.",
            "expected_answer": "Mitosis is cell division that produces two identical daughter cells for growth and repair.",
            "grade_level": 10,
            "topic": "Cell Division",
            "language": "en",
        },
        {
            "id": "tutor-photosynthesis",
            "type": "tutor",
            "question": "What is photosynthesis?",
            "expected_answer": "Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen.",
            "grade_level": 10,
            "topic": "Photosynthesis",
            "language": "en",
        },
        {
            "id": "tutor-amharic",
            "type": "tutor",
            "question": "ሴል ምንድን ነው?",
            "expected_answer": "ሴል የሕይወት መሠረታዊ አሃድ ነው።",
            "grade_level": 9,
            "topic": "Cell Biology",
            "language": "am",
        },
        {
            "id": "quiz-genetics",
            "type": "quiz",
            "question": "Generate a quiz about Genetics for Grade 11",
            "expected_answer": "Questions about DNA, genes, chromosomes, inheritance patterns",
            "grade_level": 11,
            "topic": "Genetics",
            "language": "en",
        },
        {
            "id": "lesson-ecology",
            "type": "lesson_plan",
            "question": "Create a lesson plan about Ecology for Grade 10",
            "expected_answer": "Lesson plan with objective, activities, assessment about ecosystems",
            "grade_level": 10,
            "topic": "Ecology",
            "language": "en",
        },
        {
            "id": "parent-summary",
            "type": "parent_summary",
            "question": "Generate a weekly summary for a Grade 9 student",
            "expected_answer": "Summary of topics covered, performance, and recommendations",
            "grade_level": 9,
            "topic": "General",
            "language": "en",
        },
    ]


async def evaluate_with_ragas(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
) -> dict:
    """Run Ragas evaluation on a set of QA pairs.

    Requires datasets + ragas packages installed.
    Falls back to heuristic scoring if Ragas unavailable.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
        dataset = Dataset.from_dict(data)
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
        )
        return {
            "faithfulness": result.get("faithfulness", 0),
            "answer_relevancy": result.get("answer_relevancy", 0),
            "context_recall": result.get("context_recall", 0),
            "context_precision": result.get("context_precision", 0),
        }
    except ImportError:
        return _heuristic_eval(questions, answers, contexts, ground_truths)
    except Exception as e:
        return {"error": str(e)}


def _heuristic_eval(
    questions: list[str], answers: list[str], contexts: list[list[str]], ground_truths: list[str]
) -> dict:
    """Fallback heuristic evaluation when Ragas is not available."""
    faithfulness_scores = []
    for answer, context_list in zip(answers, contexts):
        context_text = " ".join(context_list).lower()
        answer_lower = answer.lower()
        overlap = sum(1 for word in answer_lower.split() if word in context_text)
        score = min(overlap / max(len(answer_lower.split()), 1), 1.0)
        faithfulness_scores.append(score)

    relevancy_scores = []
    for answer, question in zip(answers, questions):
        q_words = set(question.lower().split())
        a_words = set(answer.lower().split())
        overlap = len(q_words & a_words)
        score = min(overlap / max(len(q_words), 1), 1.0)
        relevancy_scores.append(score)

    return {
        "faithfulness": sum(faithfulness_scores) / max(len(faithfulness_scores), 1),
        "answer_relevancy": sum(relevancy_scores) / max(len(relevancy_scores), 1),
        "context_recall": 0.0,
        "context_precision": 0.0,
        "method": "heuristic",
    }


async def run_evaluation(
    answers: list[str],
    contexts: list[list[str]],
    gold_ids: Optional[list[str]] = None,
) -> dict:
    gold_set = load_gold_set()
    if gold_ids:
        gold_set = [g for g in gold_set if g["id"] in gold_ids]

    questions = [g["question"] for g in gold_set]
    ground_truths = [g["expected_answer"] for g in gold_set]

    return await evaluate_with_ragas(questions, answers, contexts, ground_truths)


if __name__ == "__main__":
    import asyncio

    async def main():
        print(f"Gold set: {len(load_gold_set())} items")
        print("Evaluation module ready.")
        print("Use: from src.evaluation.ragas_test import run_evaluation")
        print("     results = await run_evaluation(answers, contexts)")

    asyncio.run(main())
