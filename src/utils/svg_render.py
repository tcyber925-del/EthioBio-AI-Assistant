import cairosvg
from defusedxml import minidom


def validate_svg(svg: str) -> bool:
    try:
        minidom.parseString(svg)
        return True
    except Exception:
        return False


def render_svg_to_png(
    svg: str,
    width: int = 800,
    height: int = 600,
) -> bytes:
    if not validate_svg(svg):
        raise ValueError("Failed to render SVG: invalid XML")
    try:
        return cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            output_width=width,
            output_height=height,
        )
    except Exception as e:
        raise ValueError(f"Failed to render SVG: {e}") from e
