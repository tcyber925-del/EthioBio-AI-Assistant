import json
from typing import Optional

from src.schemas.diagram import DiagramLabel
from src.utils.svg_render import validate_svg

CRITIC_SYSTEM_PROMPT = (
    "You are a diagram quality critic. "
    "Evaluate the diagram SVG and return a JSON object with:\n"
    '- "score": float from 0 to 10 (10 = perfect educational diagram)\n'
    '- "issues": list of strings describing what needs improvement\n'
    "Consider: visual clarity, educational value, "
    "label readability, and SVG correctness."
)


class DiagramCritic:
    def __init__(self, llm_router):
        self.llm_router = llm_router

    def check_xml_validity(self, svg: str) -> bool:
        return validate_svg(svg)

    def check_label_bounds(
        self,
        labels: list[DiagramLabel],
        viewbox: tuple[int, int] = (800, 600),
    ) -> list[str]:
        issues: list[str] = []
        vw, vh = viewbox
        for label in labels:
            if label.x < 0 or label.x > vw or label.y < 0 or label.y > vh:
                issues.append(
                    f"Label '{label.text}' (id={label.id}) "
                    f"is outside viewbox at ({label.x}, {label.y})"
                )
        return issues

    def score(
        self,
        svg: str,
        labels: list[DiagramLabel],
        viewbox: tuple[int, int] = (800, 600),
    ) -> float:
        score = 10.0
        if not self.check_xml_validity(svg):
            score -= 4.0
        bounds_issues = self.check_label_bounds(labels, viewbox)
        score -= len(bounds_issues) * 1.5
        return max(0.0, min(10.0, score))

    async def critique(
        self,
        svg: str,
        labels: list[DiagramLabel],
        prompt: str,
        use_llm: bool = False,
        viewbox: tuple[int, int] = (800, 600),
    ) -> dict:
        heuristic_score = self.score(svg, labels, viewbox)
        heuristic_issues = self.check_label_bounds(labels, viewbox)
        if not self.check_xml_validity(svg):
            heuristic_issues.append("SVG XML is not well-formed")

        if use_llm:
            try:
                response = await self.llm_router.route(
                    messages=[
                        {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                f"Prompt: {prompt}\n\n"
                                f"SVG:\n{svg}\n\n"
                                f"Labels: {[label.model_dump() for label in labels]}\n\n"
                                f"Current heuristic score: {heuristic_score}/10\n"
                                "Respond with JSON only."
                            ),
                        },
                    ],
                    request_type="diagram_critique",
                    temperature=0.3,
                    max_tokens=1024,
                )
                content = response["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                parsed = json.loads(content)
                llm_score = float(parsed.get("score", heuristic_score))
                llm_issues = parsed.get("issues", [])
                combined_issues = list(dict.fromkeys(heuristic_issues + llm_issues))
                return {
                    "score": max(0.0, min(10.0, llm_score)),
                    "issues": combined_issues,
                    "heuristic_score": heuristic_score,
                    "llm_score": llm_score,
                }
            except Exception:
                pass

        return {
            "score": heuristic_score,
            "issues": heuristic_issues,
        }

    async def refine(
        self,
        agent,
        prompt: str,
        topic: str,
        difficulty: str = "beginner",
        grade: int = 10,
        max_iterations: int = 3,
    ) -> dict:
        best: Optional[dict] = None
        current_prompt = prompt

        for iteration in range(max_iterations):
            result = await agent.generate(
                prompt=current_prompt,
                topic=topic,
                difficulty=difficulty,
                grade=grade,
            )

            svg = result.get("diagram_svg", "")
            labels_data = result.get("labels", [])
            labels = [
                DiagramLabel(**item) if isinstance(item, dict) else item
                for item in labels_data
            ]

            critique_result = await self.critique(svg=svg, labels=labels, prompt=current_prompt)
            score = critique_result["score"]
            issues = critique_result["issues"]

            entry = {
                "svg": svg,
                "labels": labels_data,
                "score": score,
                "issues": issues,
                "title": result.get("title", ""),
            }

            if best is None or score > best["score"]:
                best = entry

            if score >= 7:
                break

            if issues:
                current_prompt = (
                    f"{prompt}\n\n"
                    f"Revision needed (attempt {iteration + 1}/{max_iterations}). "
                    f"Previous score: {score}/10. "
                    f"Issues to fix:\n" + "\n".join(f"- {i}" for i in issues)
                )

        assert best is not None
        return best
