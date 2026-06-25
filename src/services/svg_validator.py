import io
from typing import Optional

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]

import numpy as np
from PIL import Image

from src.utils.svg_render import render_svg_to_png


class SvgImageValidator:
    def __init__(self, target_width: int = 800, target_height: int = 600):
        self.target_width = target_width
        self.target_height = target_height

    def _resize(self, arr: np.ndarray, w: int, h: int) -> np.ndarray:
        if cv2 is not None:
            return cv2.resize(arr, (w, h))
        from PIL import Image as PilImage
        img = PilImage.fromarray(arr)
        return np.array(img.resize((w, h), PilImage.LANCZOS), dtype=np.uint8)

    def validate(
        self,
        svg: str,
        reference_bytes: bytes,
    ) -> dict:
        svg_png = self._render_svg(svg)
        if svg_png is None:
            return {"score": 0.0, "mse": 1.0, "histogram_similarity": 0.0,
                     "error": "SVG rendering failed"}

        svg_array = self._bytes_to_grayscale(svg_png)
        ref_array = self._bytes_to_grayscale(reference_bytes)

        if svg_array.shape != ref_array.shape:
            ref_array = self._resize(ref_array, self.target_width, self.target_height)
            svg_array = self._resize(svg_array, self.target_width, self.target_height)

        mse = float(np.mean((svg_array.astype("float") - ref_array.astype("float")) ** 2))
        mse_score = max(0.0, 100.0 - (mse / 10.0))

        hist_sim = self._histogram_similarity(svg_array, ref_array)

        score = round(mse_score * 0.6 + hist_sim * 100 * 0.4, 2)
        score = max(0.0, min(100.0, score))

        return {
            "score": score,
            "mse": round(mse, 4),
            "histogram_similarity": round(hist_sim, 4),
            "error": None,
        }

    def _render_svg(self, svg: str) -> Optional[bytes]:
        try:
            return render_svg_to_png(svg, width=self.target_width, height=self.target_height)
        except Exception:
            return None

    @staticmethod
    def _bytes_to_grayscale(data: bytes) -> np.ndarray:
        img = Image.open(io.BytesIO(data)).convert("L")
        return np.array(img, dtype=np.uint8)

    @staticmethod
    def _histogram_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
        if cv2 is not None:
            hist1 = cv2.calcHist([img1], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([img2], [0], None, [256], [0, 256])
            cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            result = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return max(0.0, float(result))
        hist1, _ = np.histogram(img1, bins=256, range=(0, 256))
        hist2, _ = np.histogram(img2, bins=256, range=(0, 256))
        hist1 = hist1.astype(float)
        hist2 = hist2.astype(float)
        hist1 /= hist1.sum() or 1
        hist2 /= hist2.sum() or 1
        correlation = float(np.correlate(hist1, hist2)[0])
        return max(0.0, min(1.0, correlation))
