import logging
from pathlib import Path

import pypdfium2 as pdfium
from docling.document_converter import DocumentConverter
from PIL import Image

logger = logging.getLogger(__name__)

FIGURE_LABELS = {"figure", "picture", "figure_group", "picture_group"}
CROP_PADDING = 10
JPEG_QUALITY = 85


def _detect_figures(doc) -> list:
    """Find figure and picture items in a Docling document."""
    figures = []
    for item in doc.body:
        label = getattr(item, "label", None)
        if label and isinstance(label, str) and label.lower() in FIGURE_LABELS:
            figures.append(item)
        elif label and hasattr(label, "value") and str(label.value).lower() in FIGURE_LABELS:
            figures.append(item)
    return figures


def _render_page(filepath: str, page_num: int, dpi: float = 200) -> Image.Image:
    """Render a PDF page to a PIL Image at given DPI."""
    with pdfium.PdfDocument(filepath) as pdf_doc:
        page = pdf_doc[page_num - 1]
        scale = dpi / 72.0
        bitmap = page.render(scale=scale)
        pil_image = Image.frombytes(
            "RGB",
            (bitmap.width, bitmap.height),
            bitmap.format("RGB").tobytes(),
        )
    return pil_image


def _crop_figure(page_image: Image.Image, bbox, dpi: float = 200) -> Image.Image:
    """Crop figure from page image using Docling bounding box.

    Docling bbox is in PDF points (1/72 inch) with origin at bottom-left.
    PIL image coords have origin at top-left.
    """
    scale = dpi / 72.0
    width, height = page_image.size
    pts_height = height / scale

    left = max(0, int(bbox.l * scale - CROP_PADDING))
    top = max(0, int((pts_height - bbox.t) * scale - CROP_PADDING))
    right = min(width, int(bbox.r * scale + CROP_PADDING))
    bottom = min(height, int((pts_height - bbox.b) * scale + CROP_PADDING))

    if left >= right or top >= bottom:
        return page_image

    return page_image.crop((left, top, right, bottom))


def _map_unit_topic(doc, figure: object) -> tuple[str, str]:
    """Determine unit and topic by finding the nearest preceding heading."""
    figure_idx = -1
    for i, item in enumerate(doc.body):
        if item is figure:
            figure_idx = i
            break

    if figure_idx < 0:
        return "unknown", "unknown"

    unit = "unknown"
    topic = "unknown"
    for item in doc.body[:figure_idx]:
        label = getattr(item, "label", None)
        label_str = str(label.value if hasattr(label, "value") else label).lower() if label else ""
        if label_str in ("heading", "heading_level_1", "heading_level_2") or "heading" in label_str:
            text = getattr(item, "text", "") or ""
            if text.lower().startswith("unit"):
                if ":" in text:
                    parts = text.split(":", 1)
                    unit = parts[0].strip()
                    if topic == "unknown":
                        topic = parts[1].strip()
                else:
                    unit = text.strip()
            elif unit != "unknown" and topic == "unknown":
                topic = text.strip()

    return unit, topic


def _extract_caption(doc, figure: object, max_distance: int = 3) -> str:
    """Find caption text items near the figure in document order."""
    figure_idx = -1
    for i, item in enumerate(doc.body):
        if item is figure:
            figure_idx = i
            break

    if figure_idx < 0:
        # Fallback: identity comparison may fail when figure is a different
        # object than the one in doc.body (e.g., in tests using MagicMock).
        # Search again by matching the figure's label string.
        fig_label = getattr(figure, "label", None)
        if fig_label:
            fig_str = str(fig_label.value if hasattr(fig_label, "value") else fig_label).lower()
            for i, item in enumerate(doc.body):
                item_label = getattr(item, "label", None)
                if not item_label:
                    continue
                item_val = str(
                    item_label.value if hasattr(item_label, "value") else item_label
                ).lower()
                if item_val == fig_str:
                    figure_idx = i
                    break

    if figure_idx < 0:
        return ""

    for item in doc.body[figure_idx : figure_idx + max_distance + 1]:
        label = getattr(item, "label", None)
        label_str = str(label.value if hasattr(label, "value") else label).lower() if label else ""
        if "caption" in label_str:
            return getattr(item, "text", "") or ""

    return ""


def extract_figures_from_pdf(
    filepath: str,
    grade: int,
    output_dir: str = "data/diagrams",
    dpi: float = 200,
) -> list[dict]:
    """Detect and extract figures from a PDF textbook page.

    Returns list of dicts with keys:
    image_path, grade, pdf_stem, fig_num, page_num, caption, unit, topic
    """
    filepath = str(Path(filepath).resolve())
    output_root = Path(output_dir)

    converter = DocumentConverter()
    result = converter.convert(filepath)
    doc = result.document

    figures = _detect_figures(doc)
    pdf_stem = Path(filepath).stem
    extracted = []

    for fig_num, figure in enumerate(figures, 1):
        if not figure.prov:
            continue

        page_num = figure.prov[0].page
        bbox = figure.prov[0].bbox
        if bbox is None:
            continue

        page_image = _render_page(filepath, page_num, dpi=dpi)
        cropped = _crop_figure(page_image, bbox, dpi=dpi)

        unit, topic = _map_unit_topic(doc, figure)
        caption = _extract_caption(doc, figure)

        output_path = output_root / str(grade) / f"{pdf_stem}_{fig_num}.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(str(output_path), "JPEG", quality=JPEG_QUALITY)

        extracted.append(
            {
                "image_path": str(output_path),
                "grade": grade,
                "pdf_stem": pdf_stem,
                "fig_num": fig_num,
                "page_num": page_num,
                "caption": caption,
                "unit": unit,
                "topic": topic,
            }
        )
        logger.info("extracted_figure path=%s grade=%s page=%s", output_path, grade, page_num)

    return extracted
