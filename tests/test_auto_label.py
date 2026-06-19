from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.schemas.diagram import AutoLabelBatchResponse, AutoLabelRequest, AutoLabelResponse


class TestAutoLabelSchemas:
    def test_auto_label_request(self):
        req = AutoLabelRequest(diagram_id=str(uuid4()))
        assert req.diagram_id is not None

    def test_auto_label_response(self):
        from src.schemas.diagram import DiagramLabel
        resp = AutoLabelResponse(
            diagram_id=str(uuid4()), caption="Cell diagram",
            labels_count=3,
            labels=[DiagramLabel(id="l1", text="Nucleus", x=10, y=20)],
        )
        assert resp.labels_count == 3

    def test_auto_label_batch_response(self):
        resp = AutoLabelBatchResponse(processed=5, skipped=1, results=[])
        assert resp.processed == 5


class TestAutoLabelEndpoint:
    @patch("src.api.diagram.ModelRouter")
    @patch("src.api.diagram.DiagramAgent")
    async def test_auto_label_single(self, MockAgent, MockRouter):
        mock_router = AsyncMock()
        mock_router.close = AsyncMock()
        MockRouter.return_value = mock_router

        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value={
            "labels": [{"id": "l1", "text": "Nucleus", "x": 10, "y": 20}],
        })
        MockAgent.return_value = mock_agent

        from src.api.diagram import auto_label_textbook_diagram
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_session = AsyncMock()
        mock_diagram = AsyncMock()
        mock_diagram.id = uuid4()
        mock_diagram.caption = "Cell diagram"
        mock_diagram.topic = "biology"
        mock_diagram.grade_level = 10
        mock_session.get = AsyncMock(return_value=mock_diagram)

        result = await auto_label_textbook_diagram(
            request=AutoLabelRequest(diagram_id=str(mock_diagram.id)),
            session=mock_session,
        )
        assert isinstance(result, AutoLabelResponse)
        assert result.labels_count == 1
        mock_agent.generate.assert_awaited_once()
        assert mock_diagram.ground_truth_labels == {"labels": [{"id": "l1", "text": "Nucleus", "x": 10, "y": 20}]}

    @patch("src.api.diagram.ModelRouter")
    @patch("src.api.diagram.DiagramAgent")
    async def test_auto_label_not_found(self, MockAgent, MockRouter):
        from src.api.diagram import auto_label_textbook_diagram
        from fastapi import HTTPException

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await auto_label_textbook_diagram(
                request=AutoLabelRequest(diagram_id=str(uuid4())),
                session=mock_session,
            )
        assert exc.value.status_code == 404
