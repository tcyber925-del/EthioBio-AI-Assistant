def build_personalization_block(
    learner_profile_block: str,
    grade_level: int | None,
    language: str,
    misconceptions: list[str],
) -> str:
    if not learner_profile_block:
        return ""

    lines = ["## Learner Profile"]
    if grade_level:
        lines.append(f"- Grade Level: {grade_level}")
    lines.append(f"- Language: {language}")

    lines.append("")
    lines.append("### Learner Data")
    lines.append(learner_profile_block)

    if misconceptions:
        lines.append("")
        lines.append("### Known Misconceptions")
        for m in misconceptions:
            lines.append(f"- {m}")

    return "\n".join(lines)
