"""Feedback processor for the iterative retrieval loop.

Converts missing_information and coverage analysis into targeted
retrieval directives for the next iteration."""

import logging

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """Generates retrieval feedback from sufficiency gaps.

    Each gap in missing_information becomes a targeted directive.
    When missing_information is empty but coverage is low,
    generates a broader search directive.
    """

    def process(
        self,
        missing_information: list[str],
        coverage_score: float,
    ) -> list[str]:
        directives: list[str] = []

        for gap in missing_information:
            directive = f"Find information about: {gap}"
            directives.append(directive)

        if not missing_information and coverage_score < 0.5:
            directives.append(
                "Broaden search scope — coverage is low but no specific gaps identified"
            )

        if directives:
            logger.info(
                "feedback_generated count=%s from_gaps=%s",
                len(directives),
                len(missing_information),
            )

        return directives
