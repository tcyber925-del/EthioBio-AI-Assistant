from src.telegram.i18n import t
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def lesson_features_keyboard(features: dict | None = None, language: str = "en"):
    f = features or {}

    def check(key):
        return "✅" if f.get(key, False) else "⬜"

    buttons = [
        [
            InlineKeyboardButton(
                f"{check('exit_ticket')} {t('lesson.feature_exit_ticket', language)}",
                callback_data="lesson_feature_exit_ticket",
            )
        ],
        [
            InlineKeyboardButton(
                f"{check('differentiation')} {t('lesson.feature_differentiation', language)}",
                callback_data="lesson_feature_differentiation",
            )
        ],
        [
            InlineKeyboardButton(
                f"{check('diagram_suggestions')} {t('lesson.feature_diagrams', language)}",
                callback_data="lesson_feature_diagrams",
            )
        ],
        [
            InlineKeyboardButton(
                f"{check('misconception_activities')} {t('lesson.feature_misconceptions', language)}",  # noqa: E501
                callback_data="lesson_feature_misconceptions",
            )
        ],
        [
            InlineKeyboardButton(
                t("lesson.features_done", language), callback_data="lesson_features_done"
            )
        ],
        [InlineKeyboardButton(t("back", language), callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def main_menu_keyboard(socratic_enabled: bool = False, language: str = "en"):
    socratic_label = t("socratic_on", language) if socratic_enabled else t("socratic_off", language)
    buttons = [
        [InlineKeyboardButton(t("ask_question", language), callback_data="tutor")],
        [InlineKeyboardButton(t("take_quiz", language), callback_data="quiz")],
        [InlineKeyboardButton(t("my_progress", language), callback_data="progress")],
        [InlineKeyboardButton(socratic_label, callback_data="socratic_toggle")],
        [InlineKeyboardButton(t("language_btn", language), callback_data="language")],
        [InlineKeyboardButton(t("teacher_tools", language), callback_data="teacher_tools")],
        [InlineKeyboardButton(t("help_btn", language), callback_data="help")],
    ]
    return InlineKeyboardMarkup(buttons)


def teacher_tools_keyboard(language: str = "en"):
    buttons = [
        [InlineKeyboardButton(t("copilot_chat", language), callback_data="copilot")],
        [InlineKeyboardButton(t("create_lesson_plan", language), callback_data="lesson_plan")],
        [InlineKeyboardButton(t("review_quizzes", language), callback_data="open_quizzes")],
        [InlineKeyboardButton(t("upload_material", language), callback_data="upload_hint")],
        [InlineKeyboardButton(t("open_dashboard", language), callback_data="open_dashboard")],
        [InlineKeyboardButton(t("back_to_menu", language), callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def language_keyboard(language: str = "en"):
    buttons = [
        [InlineKeyboardButton(t("language.en_label", language), callback_data="lang_en")],
        [InlineKeyboardButton(t("language.am_label", language), callback_data="lang_am")],
        [InlineKeyboardButton(t("language.both_label", language), callback_data="lang_both")],
        [InlineKeyboardButton(t("back", language), callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def quiz_type_keyboard(language: str = "en"):
    buttons = [
        [InlineKeyboardButton(t("quiz.type_mc", language), callback_data="quiztype_mc")],
        [InlineKeyboardButton(t("quiz.type_tf", language), callback_data="quiztype_tf")],
        [InlineKeyboardButton(t("quiz.type_mixed", language), callback_data="quiztype_mixed")],
        [InlineKeyboardButton(t("back", language), callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def grade_keyboard(callback_prefix: str = "grade", language: str = "en"):
    buttons = []
    row = []
    for grade in range(7, 13):
        row.append(
            InlineKeyboardButton(
                t("common.grade_label", language, grade=grade),
                callback_data=f"{callback_prefix}_{grade}",
            )
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(t("back", language), callback_data="menu")])
    return InlineKeyboardMarkup(buttons)


def subject_keyboard(callback_prefix: str = "subject", language: str = "en"):
    subjects = [
        ("biology", "subject.biology"),
        ("chemistry", "subject.chemistry"),
        ("physics", "subject.physics"),
        ("mathematics", "subject.mathematics"),
    ]
    buttons = []
    for code, label_key in subjects:
        label = t(label_key, language)
        if code != "biology":
            label = f"{label}{t('subject.coming_soon_tag', language)}"
        buttons.append(
            [InlineKeyboardButton(label, callback_data=f"{callback_prefix}_{code}")]
        )
    buttons.append([InlineKeyboardButton(t("back", language), callback_data="menu")])
    return InlineKeyboardMarkup(buttons)


def answer_options_keyboard(options: list[str], language: str = "en") -> InlineKeyboardMarkup:
    """Create inline buttons from multiple choice options (single-letter buttons)."""
    letters = ["A", "B", "C", "D", "E", "F"]
    buttons = []
    for i in range(min(len(options), len(letters))):
        buttons.append([InlineKeyboardButton(letters[i], callback_data=f"ans_{letters[i]}")])
    buttons.append([InlineKeyboardButton(t("end_quiz", language), callback_data="quiz_end")])
    return InlineKeyboardMarkup(buttons)


def tf_keyboard(language: str = "en") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(t("true", language), callback_data="ans_True")],
        [InlineKeyboardButton(t("false", language), callback_data="ans_False")],
        [InlineKeyboardButton(t("end_quiz", language), callback_data="quiz_end")],
    ]
    return InlineKeyboardMarkup(buttons)


def quiz_next_keyboard(language: str = "en") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(t("next_question", language), callback_data="quiz_next")],
        [InlineKeyboardButton(t("end_quiz", language), callback_data="quiz_end")],
    ]
    return InlineKeyboardMarkup(buttons)


def quiz_result_keyboard(language: str = "en") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(t("retry_quiz", language), callback_data="quiz_retry")],
        [InlineKeyboardButton(t("new_quiz", language), callback_data="quiz")],
        [InlineKeyboardButton(t("main_menu", language), callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def back_keyboard(language: str = "en"):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("back_to_menu", language), callback_data="menu")]]
    )


def model_providers_keyboard(models: list[dict]) -> list[list[InlineKeyboardButton]]:
    """Build inline keyboard for provider selection."""
    providers = sorted({m["provider"] for m in models})
    buttons = []
    for p in providers:
        count = sum(1 for m in models if m["provider"] == p)
        label = f"{p.capitalize()} ({count} models)"
        buttons.append([InlineKeyboardButton(label, callback_data=f"model:provider:{p}")])
    buttons.append([InlineKeyboardButton("🔄 Refresh Models", callback_data="model:refresh")])
    buttons.append([InlineKeyboardButton("Back", callback_data="model:back")])
    return buttons


def provider_models_keyboard(
    models: list[dict], active_model: str
) -> list[list[InlineKeyboardButton]]:
    """Build inline keyboard for models.
    Models are pre-filtered by provider. Uses index-based callback_data
    to stay within Telegram's 64-byte limit."""
    buttons = []
    for i, m in enumerate(models):
        check = "✓ " if m["id"] == active_model else ""
        label = f"{check}{m['name']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"m:{i}")])
    buttons.append(
        [InlineKeyboardButton("← Back to Providers", callback_data="model:back_providers")]
    )
    return buttons


def socratic_toggle_keyboard(socratic_enabled: bool = False, language: str = "en"):
    label = "🧠 Turn OFF" if socratic_enabled else "🧠 Turn ON"
    data = "socratic_off" if socratic_enabled else "socratic_on"
    buttons = [
        [InlineKeyboardButton(label, callback_data=data)],
        [InlineKeyboardButton(t("back_to_menu", language), callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def hint_keyboard(hint_level: int = 0, reveal_answer: bool = False, language: str = "en"):
    if reveal_answer:
        buttons = [
            [InlineKeyboardButton(t("back_to_menu", language), callback_data="menu")],
        ]
    else:
        next_hint = hint_level + 1
        buttons = []
        if next_hint <= 3:
            labels = {
                1: t("broad_hint", language),
                2: t("specific_hint", language),
                3: t("strong_hint", language),
            }
            buttons.append(
                [InlineKeyboardButton(labels[next_hint], callback_data=f"hint_{next_hint}")]
            )
        buttons.append(
            [InlineKeyboardButton(t("reveal_answer", language), callback_data="reveal_answer")]
        )
        buttons.append([InlineKeyboardButton(t("back_to_menu", language), callback_data="menu")])
    return InlineKeyboardMarkup(buttons)
