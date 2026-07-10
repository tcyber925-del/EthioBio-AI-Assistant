from src.core.teacher_copilot.intent_router import IntentRouter


class TestIntentRouter:
    def setup_method(self):
        self.router = IntentRouter()

    async def test_student_analysis_intent(self):
        intent, confidence, reason = await self.router.classify(
            "Why is Hana struggling with cell biology?"
        )
        assert intent == "student_analysis"
        assert confidence > 0
        assert "struggling" in reason

    async def test_classroom_analysis_intent(self):
        intent, confidence, reason = await self.router.classify(
            "Who needs attention in Grade 10 Biology?"
        )
        assert intent == "classroom_analysis"
        assert confidence > 0
        assert "who needs" in reason

    async def test_intervention_guidance_intent(self):
        intent, confidence, reason = await self.router.classify(
            "What remediation strategy should I use for weak areas?"
        )
        assert intent == "intervention_guidance"
        assert confidence > 0
        assert "remediation" in reason

    async def test_curriculum_analysis_intent(self):
        intent, confidence, reason = await self.router.classify(
            "What topics come after mitosis in the curriculum?"
        )
        assert intent == "curriculum_analysis"
        assert confidence > 0

    async def test_lesson_planning_intent(self):
        intent, confidence, reason = await self.router.classify(
            "Create a lesson plan for photosynthesis tomorrow"
        )
        assert intent == "lesson_planning"
        assert confidence > 0

    async def test_assessment_creation_intent(self):
        intent, confidence, reason = await self.router.classify("Generate a quiz on genetics")
        assert intent == "assessment_creation"
        assert confidence > 0

    async def test_empty_message_defaults_to_classroom(self):
        intent, confidence, reason = await self.router.classify("")
        assert intent == "classroom_analysis"
        assert confidence >= 0.3

    async def test_confidence_is_reasonable(self):
        _, confidence, _ = await self.router.classify("How is Hana's progress?")
        assert 0 <= confidence <= 1.0

    async def test_multiple_keyword_matches_boost_confidence(self):
        _, c1, _ = await self.router.classify("student")
        _, c2, _ = await self.router.classify("student progress performance mastery")
        assert c2 >= c1
