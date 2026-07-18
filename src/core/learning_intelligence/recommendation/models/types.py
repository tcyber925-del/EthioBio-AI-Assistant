from enum import Enum


class LearningActionType(str, Enum):
    REVIEW_TOPIC = "review_topic"
    TAKE_QUIZ = "take_quiz"
    COMPLETE_RECOVERY_TASK = "complete_recovery_task"
    REVISE_MISCONCEPTION = "revise_misconception"
    STUDY_DIAGRAM = "study_diagram"
    READ_CONTENT = "read_content"
    ASK_TUTOR = "ask_tutor"
    EXAM_PRACTICE = "exam_practice"
    MAINTAIN_STREAK = "maintain_streak"
