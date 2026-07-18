TEACHER_INTENTS = {
    "student_analysis": {
        "keywords": [
            "student",
            "hana",
            "why is",
            "struggling",
            "performance",
            "mastery",
            "progress",
        ],
        "description": "Individual student performance analysis",
    },
    "classroom_analysis": {
        "keywords": [
            "classroom",
            "class",
            "who needs",
            "attention",
            "trends",
            "overview",
            "summary",
        ],
        "description": "Classroom-wide intelligence and trends",
    },
    "intervention_guidance": {
        "keywords": [
            "intervention",
            "what should i do",
            "help",
            "remediation",
            "strategy",
            "support",
        ],
        "description": "Intervention recommendations and strategies",
    },
    "curriculum_analysis": {
        "keywords": [
            "curriculum",
            "prerequisite",
            "topic",
            "what comes next",
            "coverage",
            "sequence",
        ],
        "description": "Curriculum structure and dependencies",
    },
    "lesson_planning": {
        "keywords": ["lesson", "plan", "teach", "tomorrow", "prepare", "activity", "create"],
        "description": "Lesson plan generation and preparation",
    },
    "assessment_creation": {
        "keywords": ["quiz", "test", "assessment", "exam", "question", "diagnostic", "exit ticket"],
        "description": "Assessment and quiz generation",
    },
}


class IntentRouter:
    async def classify(self, message: str) -> tuple[str, float, str]:
        message_lower = message.lower()
        best_intent = "classroom_analysis"
        best_score = 0.0
        best_reason = ""

        for intent_name, intent_config in TEACHER_INTENTS.items():
            score = 0.0
            matched = []
            for keyword in intent_config["keywords"]:
                if keyword in message_lower:
                    score += 1.0
                    matched.append(keyword)

            if score > best_score:
                best_score = score
                best_intent = intent_name
                if matched:
                    best_reason = f"Matched keywords: {', '.join(matched)}"
                else:
                    best_reason = "Default intent"

        max_possible = max(len(c["keywords"]) for c in TEACHER_INTENTS.values())
        confidence = min(best_score / max(max_possible, 1), 1.0) if best_score > 0 else 0.3

        return best_intent, confidence, best_reason
