from src.schemas.diagram import ImageValidationRequest, ImageValidationResponse
from src.services.svg_validator import SvgImageValidator


class TestSvgImageValidator:
    def test_validator_initialization(self):
        v = SvgImageValidator(target_width=400, target_height=300)
        assert v.target_width == 400

    def test_validate_identical_svg(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<rect width="100" height="100" fill="white"/>'
            '<circle cx="50" cy="50" r="30" fill="black"/>'
            "</svg>"
        )
        ref = SvgImageValidator()._render_svg(svg)
        assert ref is not None
        result = SvgImageValidator().validate(svg, ref)
        assert result["score"] > 50.0
        assert result["error"] is None

    def test_validate_different_images(self):
        svg1 = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<rect width="100" height="100" fill="white"/>'
            "</svg>"
        )
        svg2 = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<rect width="100" height="100" fill="black"/>'
            "</svg>"
        )
        ref = SvgImageValidator()._render_svg(svg2)
        assert ref is not None
        result = SvgImageValidator().validate(svg1, ref)
        assert result["score"] < 80.0

    def test_invalid_svg_returns_error(self):
        v = SvgImageValidator()
        result = v.validate("not valid svg", b"fake_reference")
        assert result["error"] is not None
        assert result["score"] == 0.0

    def test_score_between_0_and_100(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<rect width="100" height="100" fill="gray"/>'
            '<circle cx="50" cy="50" r="20" fill="black"/>'
            "</svg>"
        )
        ref = SvgImageValidator()._render_svg(svg)
        assert ref is not None
        result = SvgImageValidator().validate(svg, ref)
        assert 0.0 <= result["score"] <= 100.0
        assert 0.0 <= result["histogram_similarity"] <= 1.0
        assert result["mse"] >= 0.0


class TestImageValidationSchemas:
    def test_validation_request(self):
        req = ImageValidationRequest(svg="<svg/>", reference_image_base64="AAAA")
        assert req.svg == "<svg/>"

    def test_validation_response(self):
        resp = ImageValidationResponse(score=85.5, mse=0.02, histogram_similarity=0.95)
        assert resp.score == 85.5
        assert resp.error is None

    def test_validation_response_with_error(self):
        resp = ImageValidationResponse(score=0.0, error="Failed")
        assert resp.error == "Failed"
