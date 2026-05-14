from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("🧬 Ask a Question", callback_data="tutor")],
        [InlineKeyboardButton("📝 Take a Quiz", callback_data="quiz")],
        [InlineKeyboardButton("📊 My Progress", callback_data="progress")],
        [InlineKeyboardButton("🌐 Language", callback_data="language")],
        [InlineKeyboardButton("👨‍🏫 Teacher Tools", callback_data="teacher_tools")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ]
    return InlineKeyboardMarkup(buttons)


def teacher_tools_keyboard():
    buttons = [
        [InlineKeyboardButton("📋 Create Lesson Plan", callback_data="lesson_plan")],
        [InlineKeyboardButton("📄 Review Quizzes", callback_data="open_quizzes")],
        [InlineKeyboardButton("📈 Open Dashboard", callback_data="open_dashboard")],
        [InlineKeyboardButton("← Back to Menu", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def language_keyboard():
    buttons = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇪🇹 አማርኛ (Amharic)", callback_data="lang_am")],
        [InlineKeyboardButton("🌍 Bilingual", callback_data="lang_both")],
        [InlineKeyboardButton("← Back", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def quiz_type_keyboard():
    buttons = [
        [InlineKeyboardButton("✅ Multiple Choice", callback_data="quiztype_mc")],
        [InlineKeyboardButton("📋 True / False", callback_data="quiztype_tf")],
        [InlineKeyboardButton("🔀 Mixed", callback_data="quiztype_mixed")],
        [InlineKeyboardButton("← Back", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def grade_keyboard(callback_prefix: str = "grade"):
    buttons = []
    row = []
    for grade in range(7, 13):
        row.append(InlineKeyboardButton(f"Grade {grade}", callback_data=f"{callback_prefix}_{grade}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("← Back", callback_data="menu")])
    return InlineKeyboardMarkup(buttons)


def answer_options_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    """Create inline buttons from multiple choice options (A, B, C, D)."""
    letters = ["A", "B", "C", "D", "E", "F"]
    buttons = []
    for i, opt in enumerate(options):
        if i < len(letters):
            label = opt.split(")")[0] + ")" if ") " in opt else letters[i]
            buttons.append([InlineKeyboardButton(f"{letters[i]}) {opt.split(') ')[-1][:40]}", callback_data=f"ans_{letters[i]}")])
    buttons.append([InlineKeyboardButton("🔙 End Quiz", callback_data="quiz_end")])
    return InlineKeyboardMarkup(buttons)


def tf_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("✅ True", callback_data="ans_True")],
        [InlineKeyboardButton("❌ False", callback_data="ans_False")],
        [InlineKeyboardButton("🔙 End Quiz", callback_data="quiz_end")],
    ]
    return InlineKeyboardMarkup(buttons)


def quiz_next_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➡️ Next Question", callback_data="quiz_next")],
        [InlineKeyboardButton("🔙 End Quiz", callback_data="quiz_end")],
    ]
    return InlineKeyboardMarkup(buttons)


def quiz_result_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🔁 Retry Quiz", callback_data="quiz_retry")],
        [InlineKeyboardButton("📝 New Quiz", callback_data="quiz")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Back to Menu", callback_data="menu")]])
