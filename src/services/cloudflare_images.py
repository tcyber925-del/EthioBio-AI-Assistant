import base64
from io import BytesIO
from typing import Optional

import httpx
from PIL import Image

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4/accounts"
DEFAULT_SD_MODEL = "@cf/runwayml/stable-diffusion-v1-5-img2img"
DEFAULT_FLUX_MODEL = "@cf/black-forest-labs/flux-1-schnell"


class CloudflareImageGenerator:
    def __init__(
        self,
        account_id: str,
        api_token: str,
        http_client: Optional[httpx.AsyncClient] = None,
        default_model: str = DEFAULT_FLUX_MODEL,
    ):
        self.account_id = account_id
        self.api_token = api_token
        self._client = http_client
        self.default_model = default_model

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    @classmethod
    def from_settings(cls, settings) -> "CloudflareImageGenerator":
        return cls(
            account_id=settings.cloudflare_account_id,
            api_token=settings.cloudflare_api_token,
            default_model=settings.cloudflare_image_model or DEFAULT_FLUX_MODEL,
        )

    def _build_url(self, model: str) -> str:
        return f"{CLOUDFLARE_API_BASE}/{self.account_id}/ai/run/{model}"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_token}"}

    @staticmethod
    def _extract_image(response: httpx.Response) -> bytes:
        content_type = response.headers.get("content-type", "")
        if "image" in content_type:
            return response.content
        body = response.json()
        result = body.get("result", {})
        img_b64 = result.get("image")
        if img_b64:
            return base64.b64decode(img_b64)
        raise RuntimeError(f"Cloudflare API returned unexpected response: {body}")

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        steps: int = 4,
    ) -> bytes:
        model = model or self.default_model
        url = self._build_url(model)
        payload: dict = {"prompt": prompt}
        if "flux" in model:
            payload["steps"] = steps
        response = await self.client.post(url, headers=self._headers(), json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Cloudflare API error {response.status_code}: {response.text}")
        return self._extract_image(response)

    async def image_to_image(
        self,
        prompt: str,
        input_image: bytes,
        model: Optional[str] = None,
    ) -> bytes:
        model = model or DEFAULT_SD_MODEL
        url = self._build_url(model)
        img = Image.open(BytesIO(input_image)).convert("RGB")
        img = img.resize((512, 512), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG")
        raw_bytes = buf.getvalue()
        payload = {"prompt": prompt, "image_b64": base64.b64encode(raw_bytes).decode("utf-8")}
        response = await self.client.post(url, headers=self._headers(), json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Cloudflare API error {response.status_code}: {response.text}")
        return self._extract_image(response)
