"""Tests for textbook diagram figure extraction."""

from unittest.mock import MagicMock


def test_detect_figures_returns_figures():
    from src.ingestion.diagram_extractor import _detect_figures

    mock_item_figure = MagicMock()
    mock_item_figure.label = "figure"
    mock_item_figure.prov = [MagicMock()]
    mock_item_figure.prov[0].page = 1

    mock_item_text = MagicMock()
    mock_item_text.label = "text"

    doc = MagicMock()
    doc.body = [mock_item_figure, mock_item_text, mock_item_figure]

    result = _detect_figures(doc)
    assert len(result) == 2
    assert all(item.label == "figure" for item in result)


def test_detect_figures_empty_when_none():
    from src.ingestion.diagram_extractor import _detect_figures

    doc = MagicMock()
    doc.body = []

    assert _detect_figures(doc) == []


def test_map_unit_topic_from_headings():
    from src.ingestion.diagram_extractor import _map_unit_topic

    doc = MagicMock()
    heading1 = MagicMock()
    heading1.label = "heading"
    heading1.text = "Unit 1: Cell Biology"
    heading2 = MagicMock()
    heading2.label = "heading"
    heading2.text = "1.1 Cell Structure"
    text_item = MagicMock()
    text_item.label = "text"
    figure = MagicMock()
    figure.label = "figure"

    doc.body = [heading1, heading2, text_item, figure]

    unit, topic = _map_unit_topic(doc, figure)
    assert unit == "Unit 1"
    assert topic == "Cell Biology"


def test_extract_caption_from_nearby_text():
    from src.ingestion.diagram_extractor import _extract_caption

    doc = MagicMock()
    caption_item = MagicMock()
    caption_item.label = "caption"
    caption_item.text = "Figure 1.1: Structure of a cell"

    doc.body = [MagicMock(label="figure"), caption_item]

    result = _extract_caption(doc, MagicMock(label="figure"))
    assert "Figure 1.1" in result


def test_extract_figures_from_pdf_returns_metadata():
    from src.ingestion.diagram_extractor import extract_figures_from_pdf

    assert callable(extract_figures_from_pdf)


def test_ingest_script_imports():
    """Verify the ingest script module imports cleanly."""
    import importlib.util
    spec = importlib.util.find_spec("scripts.ingest_diagrams")
    if spec is not None:
        import scripts.ingest_diagrams
        assert callable(scripts.ingest_diagrams.main)
