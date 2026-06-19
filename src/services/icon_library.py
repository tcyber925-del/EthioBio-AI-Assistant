import json
from pathlib import Path
from typing import Optional

import structlog

from src.schemas.icon_library import IconCategory, IconEntry

logger = structlog.get_logger()

CATALOG_PATH = Path(__file__).parent.parent.parent / "data" / "icon_catalog.json"
ICONS_DIR = Path(__file__).parent.parent.parent / "data" / "icons"


class IconLibrary:
    def __init__(self, catalog_path: Path = CATALOG_PATH, icons_dir: Path = ICONS_DIR):
        self._catalog_path = catalog_path
        self._icons_dir = icons_dir
        self._catalog: list[IconEntry] | None = None
        self._categories: list[IconCategory] | None = None

    def _load_catalog(self) -> list[IconEntry]:
        if self._catalog is not None:
            return self._catalog
        if not self._catalog_path.exists():
            logger.warning("icon_catalog_not_found", path=str(self._catalog_path))
            self._catalog = []
            self._categories = []
            return self._catalog
        with open(self._catalog_path) as f:
            data = json.load(f)
        raw = data.get("icons", [])
        self._catalog = [IconEntry(**item) for item in raw]
        cats = {}
        for icon in self._catalog:
            cats[icon.category] = cats.get(icon.category, 0) + 1
        self._categories = [
            IconCategory(name=name, icon_count=count)
            for name, count in sorted(cats.items(), key=lambda x: -x[1])
        ]
        logger.info("icon_catalog_loaded", total=len(self._catalog),
                     categories=len(self._categories))
        return self._catalog

    def get_categories(self) -> list[IconCategory]:
        self._load_catalog()
        return self._categories or []

    def get_icons(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[IconEntry], int]:
        catalog = self._load_catalog()
        filtered = list(catalog)
        if category and category != "All_icons":
            filtered = [i for i in filtered if i.category == category]
        if search:
            q = search.lower()
            filtered = [
                i for i in filtered
                if q in i.name.lower() or q in i.id.lower() or q in i.category.lower()
            ]
        total = len(filtered)
        page = filtered[offset : offset + limit]
        return page, total

    def get_icon_by_id(self, icon_id: str) -> Optional[IconEntry]:
        catalog = self._load_catalog()
        for icon in catalog:
            if icon.id == icon_id:
                return icon
        return None

    def _fetch_from_github(self, icon: IconEntry) -> Optional[str]:
        path = f"static/icons/{icon.license}/{icon.category}/{icon.author}/{icon.filename}"
        url = f"https://raw.githubusercontent.com/duerrsimon/bioicons/main/{path}"
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "EthioBio/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    content = resp.read().decode("utf-8")
                    cat_dir = self._icons_dir / icon.category
                    cat_dir.mkdir(parents=True, exist_ok=True)
                    (cat_dir / icon.filename).write_text(content)
                    return content
        except Exception as e:
            logger.warning("icon_github_fetch_failed", icon_id=icon.id, error=str(e))
        return None

    def get_icon_svg(self, icon_id: str) -> Optional[str]:
        icon = self.get_icon_by_id(icon_id)
        if not icon:
            return None
        svg_path = self._icons_dir / icon.category / icon.filename
        if svg_path.exists():
            return svg_path.read_text()
        alt_path = self._icons_dir / icon.filename
        if alt_path.exists():
            return alt_path.read_text()
        return self._fetch_from_github(icon)

    def compose_from_topic(
        self,
        topic: str,
        icon_ids: list[str],
        title: str = "Diagram",
    ) -> str:
        icons_meta = []
        for iid in icon_ids:
            icon_meta = self.get_icon_by_id(iid)
            if icon_meta:
                icons_meta.append(icon_meta)

        count = len(icons_meta)
        if count == 0:
            return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
  <rect width="800" height="600" fill="#f8f9fa" rx="8"/>
  <text x="400" y="300" text-anchor="middle" font-size="20" fill="#999">{title}</text>
</svg>"""
        cols = min(4, max(1, count))
        rows = (count + cols - 1) // cols
        cell_w = 800 // cols
        cell_h = 600 // rows
        svg_parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        ]

        svg_parts.append(
            '<rect width="800" height="600" fill="#f8f9fa" rx="8"/>'
        )
        svg_parts.append(
            f'<text x="400" y="30" text-anchor="middle" font-size="20" '
            f'font-weight="bold" fill="#333">{title}</text>'
        )

        for idx, icon_meta in enumerate(icons_meta):
            col = idx % cols
            row = idx // cols
            x = col * cell_w + 10
            y = row * cell_h + 50
            svg = self.get_icon_svg(icon_meta.id)
            if svg:
                inserted = self._insert_svg_into_cell(svg, x, y, cell_w - 20, cell_h - 40)
                svg_parts.append(inserted)
            label_y = y + cell_h - 20
            svg_parts.append(
                f'<text x="{x + (cell_w - 20) / 2}" y="{label_y}" '
                f'text-anchor="middle" font-size="11" fill="#555">{icon_meta.name}</text>'
            )

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    @staticmethod
    def _insert_svg_into_cell(svg: str, x: float, y: float, w: float, h: float) -> str:
        cleaned = svg.strip()
        if cleaned.startswith("<svg"):
            cleaned = cleaned[cleaned.find(">") + 1 : cleaned.rfind("</svg>")]
        return (
            f'<g transform="translate({x},{y}) scale({min(w, h) / 200})">\n'
            f"{cleaned}\n"
            f"</g>"
        )
