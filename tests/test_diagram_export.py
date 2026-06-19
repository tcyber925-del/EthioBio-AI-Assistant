from unittest.mock import patch

import pytest

from src.schemas.diagram import DiagramExportRequest, DiagramLabel


class TestDiagramExportSchemas:
    def test_diagram_export_request_minimal(self):
        req = DiagramExportRequest(svg="<svg/>")
        assert req.format == "pdf"
        assert req.title == "Biology Diagram"

    def test_diagram_export_request_full(self):
        req = DiagramExportRequest(
            svg="<svg/>", title="Cell", topic="Biology", grade=10,
            labels=[DiagramLabel(id="l1", text="Nucleus", x=10, y=20)],
            format="docx",
        )
        assert req.format == "docx"
        assert len(req.labels) == 1


class TestDiagramExportDOCX:
    def test_export_docx_returns_bytes(self):
        from src.export.diagram_exporter import export_diagram_to_docx
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="40"/><text x="10" y="10">Nucleus</text></svg>'
        result = export_diagram_to_docx(svg, title="Cell", topic="Biology", grade=10)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_docx_with_labels(self):
        from src.export.diagram_exporter import export_diagram_to_docx
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="40"/></svg>'
        labels = [{"text": "Nucleus"}, {"text": "Cell Membrane"}]
        result = export_diagram_to_docx(svg, title="Cell", labels=labels)
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestDiagramExportPDF:
    def test_export_pdf_returns_bytes(self):
        from src.export.diagram_exporter import export_diagram_to_pdf
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'
        result = export_diagram_to_pdf(svg, title="Test", topic="Biology", grade=10)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_pdf_with_labels(self):
        from src.export.diagram_exporter import export_diagram_to_pdf
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'
        labels = [{"text": "Label 1"}, {"text": "Label 2"}]
        result = export_diagram_to_pdf(svg, title="Test", labels=labels)
        assert isinstance(result, bytes)
        assert len(result) > 0
