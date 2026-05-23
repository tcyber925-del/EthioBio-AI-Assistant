import io
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


def export_quiz_to_docx(quiz: dict[str, Any], questions: list[dict[str, Any]]) -> bytes:
    doc = Document()

    title = doc.add_heading(quiz.get("title", "Quiz"), level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta.add_run(f"Grade {quiz.get('grade_level', 'N/A')} - {quiz.get('topic', 'N/A')}")
    run.font.size = Pt(12)
    run.font.color.rgb = None

    doc.add_paragraph()

    for i, q in enumerate(questions, 1):
        q_type = q.get("question_type", "unknown").replace("_", " ").title()
        p = doc.add_paragraph()
        run = p.add_run(f"{i}. ({q_type}) {q['question_text']}")
        run.bold = True
        run.font.size = Pt(11)

        options = q.get("options")
        if options:
            for opt in options:
                doc.add_paragraph(opt, style="List Bullet")

        p_ans = doc.add_paragraph()
        run_ans = p_ans.add_run(f"Answer: {q['correct_answer']}")
        run_ans.font.size = Pt(10)
        run_ans.font.color.rgb = None

        explanation = q.get("explanation")
        if explanation:
            p_exp = doc.add_paragraph()
            run_exp = p_exp.add_run(f"Explanation: {explanation}")
            run_exp.font.size = Pt(10)
            run_exp.italic = True

        doc.add_paragraph()

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def export_lesson_plan_to_docx(lesson: dict[str, Any]) -> bytes:
    doc = Document()

    title = doc.add_heading("Lesson Plan", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta.add_run(f"Grade {lesson.get('grade_level', 'N/A')} - {lesson.get('topic', 'N/A')}")
    run.font.size = Pt(12)

    doc.add_paragraph()

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
        doc.add_heading(section_name, level=2)
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    for key, val in item.items():
                        p = doc.add_paragraph()
                        run = p.add_run(f"{key.replace('_', ' ').title()}: ")
                        run.bold = True
                        p.add_run(str(val))
                else:
                    doc.add_paragraph(str(item), style="List Bullet")
        elif content:
            doc.add_paragraph(content)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()
