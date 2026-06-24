import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.session import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"
    parent = "parent"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student)
    language_preference: Mapped[str] = mapped_column(String(10), default="en")
    grade_level: Mapped[int] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    student_profile: Mapped["StudentProfile"] = relationship(back_populates="user", uselist=False)
    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="user")
    message_threads: Mapped[list["MessageThread"]] = relationship(back_populates="user")
    feedback_events: Mapped[list["FeedbackEvent"]] = relationship(back_populates="user")
    diagram_attempts: Mapped[list["DiagramAttempt"]] = relationship(back_populates="user")

    children: Mapped[list["User"]] = relationship(
        secondary="parent_children",
        primaryjoin="User.id == ParentChild.parent_id",
        secondaryjoin="User.id == ParentChild.student_id",
        back_populates="parents",
    )
    parents: Mapped[list["User"]] = relationship(
        secondary="parent_children",
        primaryjoin="User.id == ParentChild.student_id",
        secondaryjoin="User.id == ParentChild.parent_id",
        back_populates="children",
    )


class ParentChild(Base):
    __tablename__ = "parent_children"

    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    school: Mapped[str] = mapped_column(String(200), nullable=True)
    region: Mapped[str] = mapped_column(String(100), nullable=True)
    topic_mastery: Mapped[dict] = mapped_column(JSON, default=dict)
    score_history: Mapped[dict] = mapped_column(JSON, default=list)
    weak_areas: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="student_profile")
    progress_records: Mapped[list["ProgressRecord"]] = relationship(back_populates="student")


class School(Base):
    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    class_groups: Mapped[list["ClassGroup"]] = relationship(back_populates="school")
    health_snapshots: Mapped[list["SchoolHealthSnapshot"]] = relationship(back_populates="school")


class ClassGroup(Base):
    __tablename__ = "class_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200))
    grade_level: Mapped[int] = mapped_column(Integer)
    teacher_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    students: Mapped[list["User"]] = relationship(secondary="class_enrollments")
    school: Mapped["School | None"] = relationship(back_populates="class_groups")


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("class_groups.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SchoolHealthSnapshot(Base):
    __tablename__ = "school_health_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id"))
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    avg_health: Mapped[float] = mapped_column(Float)
    total_students: Mapped[int] = mapped_column(Integer)
    at_risk_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    school: Mapped["School"] = relationship(back_populates="health_snapshots")


class CurriculumTopic(Base):
    __tablename__ = "curriculum_topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    grade_level: Mapped[int] = mapped_column(Integer)
    unit: Mapped[str] = mapped_column(String(200))
    topic: Mapped[str] = mapped_column(String(300))
    subtopic: Mapped[str] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200), nullable=True)
    embedding_id: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LessonPlan(Base):
    __tablename__ = "lesson_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    teacher_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(300))
    objective: Mapped[str] = mapped_column(Text)
    prior_knowledge: Mapped[str] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text)
    activities: Mapped[dict] = mapped_column(JSON, default=list)
    assessment: Mapped[str] = mapped_column(Text, nullable=True)
    homework: Mapped[str] = mapped_column(Text, nullable=True)
    teacher_notes: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    model_used: Mapped[str] = mapped_column(String(100), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    used_in_class: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    quiz_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=True)
    question_type: Mapped[str] = mapped_column(String(20))
    question_text: Mapped[str] = mapped_column(Text)
    options: Mapped[dict] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(300))
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    difficulty_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_ref: Mapped[str] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    teacher_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    grade_level: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(300))
    question_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    model_used: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    questions: Mapped[list["Question"]] = relationship(backref="quiz", foreign_keys="Question.quiz_id")
    attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="quiz")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    quiz_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quizzes.id"))
    score: Mapped[float] = mapped_column(Float, nullable=True)
    total: Mapped[int] = mapped_column(Integer)
    answers: Mapped[dict] = mapped_column(JSON, default=list)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="quiz_attempts")
    quiz: Mapped["Quiz"] = relationship(back_populates="attempts")


class ProgressRecord(Base):
    __tablename__ = "progress_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("student_profiles.id"))
    topic: Mapped[str] = mapped_column(String(300))
    score: Mapped[float] = mapped_column(Float)
    total: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    student: Mapped["StudentProfile"] = relationship(back_populates="progress_records")


class ParentSummary(Base):
    __tablename__ = "parent_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    parent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    summary_text: Mapped[str] = mapped_column(Text)
    summary_amharic: Mapped[str] = mapped_column(Text, nullable=True)
    week_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    week_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_low_performance_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MessageThread(Base):
    __tablename__ = "message_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(String(20), default="telegram")
    messages: Mapped[dict] = mapped_column(JSON, default=list)
    topic: Mapped[str] = mapped_column(String(300), nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="message_threads")


class ContentSource(Base):
    __tablename__ = "content_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[str] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=True)
    unit: Mapped[str] = mapped_column(String(200), nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserGamification(Base):
    __tablename__ = "user_gamification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(backref="gamification", uselist=False)


class XpEvent(Base):
    __tablename__ = "xp_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(String(50))
    amount: Mapped[int] = mapped_column(Integer)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(backref="xp_events")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    achievement_id: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    icon: Mapped[str] = mapped_column(String(50), default="🏆")
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(backref="achievements")


class RecoveryPlan(Base):
    __tablename__ = "recovery_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(300))
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(backref="recovery_plans")
    tasks: Mapped[list["RecoveryTask"]] = relationship(back_populates="plan")


class RecoveryTask(Base):
    __tablename__ = "recovery_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recovery_plans.id"))
    title: Mapped[str] = mapped_column(String(300))
    task_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    plan: Mapped["RecoveryPlan"] = relationship(back_populates="tasks")


class DiagramAttempt(Base):
    __tablename__ = "diagram_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(100))
    difficulty: Mapped[str] = mapped_column(String(20))
    score: Mapped[float] = mapped_column(Float, nullable=True)
    labels: Mapped[dict] = mapped_column(JSON, default=dict)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="diagram_attempts")


class TextbookDiagram(Base):
    __tablename__ = "textbook_diagrams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    grade_level: Mapped[int] = mapped_column(Integer)
    unit: Mapped[str] = mapped_column(String(200), default="")
    topic: Mapped[str] = mapped_column(String(200), default="")
    caption: Mapped[str] = mapped_column(Text, default="")
    image_path: Mapped[str] = mapped_column(String(500))
    figure_number: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str] = mapped_column(String(300))
    ground_truth_labels: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StudentMastery(Base):
    __tablename__ = "student_mastery"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(300))
    unit: Mapped[str] = mapped_column(String(200), nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer)
    average_score: Mapped[float] = mapped_column(Float, default=0.0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    total_questions_attempted: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    severity: Mapped[str] = mapped_column(String(20), default="good")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    last_assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(backref="mastery_records")


class MisconceptionPattern(Base):
    __tablename__ = "misconception_patterns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(300))
    pattern_type: Mapped[str] = mapped_column(String(50))
    pattern_description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(30), default="misunderstanding")
    frequency: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    common_wrong_answer: Mapped[str] = mapped_column(String(500), nullable=True)
    related_question_ids: Mapped[dict] = mapped_column(JSON, default=list)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(backref="misconception_patterns")


class MisconceptionKnowledgeEntry(Base):
    __tablename__ = "misconception_knowledge_base"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    topic: Mapped[str] = mapped_column(String(300), index=True)
    misconception: Mapped[str] = mapped_column(String(500))
    explanation: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(30), default="misconception")
    related_objectives: Mapped[dict] = mapped_column(JSON, default=list)
    recommended_strategies: Mapped[dict] = mapped_column(JSON, default=list)
    detection_patterns: Mapped[dict] = mapped_column(JSON, default=list)
    grade_level: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


INTERVENTION_TYPES = [
    "REVIEW_TOPIC", "REVISE_MISCONCEPTION", "RECOVERY_PLAN",
    "TAKE_QUIZ", "EXAM_PRACTICE", "TUTOR_SESSION", "ENGAGEMENT_BOOST",
]

INTERVENTION_STATUSES = ["planned", "active", "completed", "cancelled"]


class InterventionAssignment(Base):
    __tablename__ = "intervention_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    intervention_type: Mapped[str] = mapped_column(String(50))
    topic: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    estimated_impact: Mapped[float] = mapped_column(Float, default=0.0)
    effectiveness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(backref="intervention_assignments")


class TopicMasteryHistory(Base):
    __tablename__ = "topic_mastery_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(300))
    unit: Mapped[str] = mapped_column(String(200), nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer)
    average_score: Mapped[float] = mapped_column(Float)
    attempt_count: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(backref="mastery_history")


class SpacedRepetitionSchedule(Base):
    __tablename__ = "spaced_repetition_schedule"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(300))
    unit: Mapped[str] = mapped_column(String(200), nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer, default=0)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(backref="spaced_repetition_schedules")


class RecoveryNotification(Base):
    __tablename__ = "recovery_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    topic: Mapped[str] = mapped_column(String(300))
    event_type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    improvement_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    old_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(backref="recovery_notifications")


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    rating: Mapped[int] = mapped_column(Integer, nullable=True)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="feedback_events")


class TopicPrerequisite(Base):
    __tablename__ = "topic_prerequisites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculum_topics.id"), index=True,
    )
    prerequisite_topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculum_topics.id"), index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(20), default="prerequisite")
    grade_level: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    topic: Mapped["CurriculumTopic"] = relationship(
        foreign_keys=[topic_id], backref="prerequisites_to",
    )
    prerequisite: Mapped["CurriculumTopic"] = relationship(
        foreign_keys=[prerequisite_topic_id], backref="prerequisites_from",
    )


class ModelRoutingLog(Base):
    __tablename__ = "model_routing_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    request_type: Mapped[str] = mapped_column(String(50))
    model_used: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    retrieval_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("questions.id"))
    quiz_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=True
    )
    correct: Mapped[bool] = mapped_column(Boolean)
    time_spent: Mapped[float | None] = mapped_column(Float, nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StudentAbility(Base):
    __tablename__ = "student_abilities"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    topic: Mapped[str] = mapped_column(String(300), primary_key=True)
    ability_score: Mapped[float] = mapped_column(Float, default=0.0)
    uncertainty: Mapped[float] = mapped_column(Float, default=3.0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MemorySession(Base):
    __tablename__ = "memory_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    active_topic: Mapped[str] = mapped_column(String(300), nullable=True)
    tutoring_mode: Mapped[str] = mapped_column(String(20), default="direct")
    educational_context: Mapped[dict] = mapped_column(JSON, nullable=True)
    unresolved_questions: Mapped[dict] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    summary: Mapped[str] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(backref="memory_sessions")


class MemorySocraticState(Base):
    __tablename__ = "memory_socratic_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(300))
    socratic_stage: Mapped[str] = mapped_column(String(30), default="guided_discovery")
    current_focus: Mapped[str] = mapped_column(String(500), nullable=True)
    student_understanding: Mapped[str] = mapped_column(String(20), default="none")
    next_question: Mapped[str] = mapped_column(Text, nullable=True)
    conceptual_gaps: Mapped[dict] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(backref="memory_socratic_states")


class MemoryEducationalSummary(Base):
    __tablename__ = "memory_educational_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(300))
    understanding_level: Mapped[str] = mapped_column(String(20), nullable=True)
    key_misconceptions: Mapped[dict] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    next_learning_goal: Mapped[str] = mapped_column(Text, nullable=True)
    tutoring_quality_notes: Mapped[str] = mapped_column(Text, nullable=True)
    embedding_id: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(backref="memory_educational_summaries")


class MemoryEvent(Base):
    __tablename__ = "memory_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    topic: Mapped[str] = mapped_column(String(300), nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(backref="memory_events")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("memory_sessions.session_id"), nullable=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(300), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped["User"] = relationship(backref="conversation_turns")


class SemanticFact(Base):
    __tablename__ = "semantic_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True,
    )
    fact_key: Mapped[str] = mapped_column(String(100), index=True)
    fact_value: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    consolidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow,
    )

    user: Mapped["User"] = relationship(backref="semantic_facts")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    email: Mapped[str] = mapped_column(String(255))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    digest_frequency: Mapped[str] = mapped_column(String(20), default="never")
    milestone_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    review_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    verification_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ============================================================
# Evidence Graph Models (Agentic RAG Phase 0)
# ============================================================

class EvidenceSession(Base):
    __tablename__ = "evidence_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence_sessions.id"), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    original_query: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_query: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_score: Mapped[float] = mapped_column(Float, default=0.0)
    rerank_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    retrieved_by: Mapped[str] = mapped_column(String(50), nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    trace_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    error: Mapped[str] = mapped_column(Text, nullable=True)
    user_message: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text, nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(8), nullable=True)
    intent: Mapped[str] = mapped_column(String(64), nullable=True)
    nodes_visited: Mapped[list] = mapped_column(JSON, default=list)
    node_timings: Mapped[dict] = mapped_column(JSON, default=dict)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)


class InterventionKnowledgeEntry(Base):
    __tablename__ = "intervention_knowledge_base"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    intervention_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    intervention_type: Mapped[str] = mapped_column(String(50))
    topic: Mapped[str] = mapped_column(String(300))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    grade_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

    effectiveness_score: Mapped[float] = mapped_column(Float)
    mastery_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    readiness_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    retention_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    misconception_reduction: Mapped[float | None] = mapped_column(Float, nullable=True)

    pre_mastery_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_mastery_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    estimated_impact: Mapped[float] = mapped_column(Float, default=0.0)
    completion_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(backref="intervention_knowledge_entries")


class StudentDigitalTwin(Base):
    __tablename__ = "student_digital_twins"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    knowledge_state: Mapped[dict] = mapped_column(JSON, default=dict)
    mastery_state: Mapped[dict] = mapped_column(JSON, default=dict)
    misconception_state: Mapped[dict] = mapped_column(JSON, default=dict)
    retention_state: Mapped[dict] = mapped_column(JSON, default=dict)
    readiness_state: Mapped[dict] = mapped_column(JSON, default=dict)
    intervention_state: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_health: Mapped[str] = mapped_column(String(20), default="unknown")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    last_built_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped["User"] = relationship(backref="digital_twin", uselist=False)
