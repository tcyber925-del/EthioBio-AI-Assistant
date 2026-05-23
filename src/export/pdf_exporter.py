from typing import Any

from fpdf import FPDF


class QuizPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, "EthioBio AI Assistant", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


class LessonPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, "EthioBio AI Assistant", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def export_quiz_to_pdf(quiz: dict[str, Any], questions: list[dict[str, Any]]) -> bytes:
    pdf = QuizPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 14, quiz.get("title", "Quiz"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    meta = f"Grade {quiz.get('grade_level', 'N/A')} - {quiz.get('topic', 'N/A')}"
    pdf.cell(0, 8, meta, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    for i, q in enumerate(questions, 1):
        if pdf.get_y() > 250:
            pdf.add_page()

        q_type = q.get("question_type", "unknown").replace("_", " ").title()
        pdf.set_font("Helvetica", "B", 11)
        question_text = q["question_text"]
        pdf.multi_cell(0, 6, f"{i}. ({q_type}) {question_text}")
        pdf.ln(1)

        options = q.get("options")
        if options:
            pdf.set_font("Helvetica", "", 10)
            for opt in options:
                pdf.cell(0, 5, f"  - {opt}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 100, 0)
        pdf.multi_cell(0, 5, f"Answer: {q['correct_answer']}")
        pdf.set_text_color(0, 0, 0)

        explanation = q.get("explanation")
        if explanation:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5, f"Explanation: {explanation}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        pdf.ln(4)

    return bytes(pdf.output())


def export_lesson_plan_to_pdf(lesson: dict[str, Any]) -> bytes:
    pdf = LessonPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 14, "Lesson Plan", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    meta = f"Grade {lesson.get('grade_level', 'N/A')} - {lesson.get('topic', 'N/A')}"
    pdf.cell(0, 8, meta, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    sections = [
        ("Objective", lesson.get("objective", "")),
        ("Prior Knowledge", lesson.get("prior_knowledge", "")),
        ("Explanation", lesson.get("explanation", "")),
        ("Activities", lesson.get("activities", [])),
        ("Assessment", lesson.get("assessment", "")),
        ("Homework", lesson.get("homework", "")),
        ("Teacher Notes", lesson.get("teacher_notes", "")),
    ]

    for section_name, content in sections:
        if pdf.get_y() > 255:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, section_name, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        pdf.set_font("Helvetica", "", 10)
        if isinstance(content, list):
            for item in content:
                if pdf.get_y() > 265:
                    pdf.add_page()
                if isinstance(item, dict):
                    for key, val in item.items():
                        line = f"{key.replace('_', ' ').title()}: {val}"
                        pdf.multi_cell(0, 5, line)
                else:
                    pdf.multi_cell(0, 5, f"- {item}")
        elif content:
            pdf.multi_cell(0, 5, content)

        pdf.ln(4)

    return bytes(pdf.output())
