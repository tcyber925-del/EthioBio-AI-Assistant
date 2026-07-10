import json
from pathlib import Path

import pytest

from src.schemas.icon_library import (
    IconCategory,
    IconComposeRequest,
    IconComposeResponse,
    IconEntry,
    IconListResponse,
    PlacedIcon,
)
from src.services.icon_library import IconLibrary


@pytest.fixture
def sample_catalog(tmp_path: Path) -> Path:
    icons = [
        {
            "id": "dna",
            "name": "Dna",
            "category": "Genetics",
            "author": "test",
            "license": "cc-0",
            "path": "",
            "filename": "dna.svg",
            "grade_tags": [],
        },
        {
            "id": "cell",
            "name": "Cell",
            "category": "Cell_types",
            "author": "test",
            "license": "cc-0",
            "path": "",
            "filename": "cell.svg",
            "grade_tags": [],
        },
        {
            "id": "mitosis",
            "name": "Mitosis",
            "category": "Cell_types",
            "author": "test",
            "license": "cc-0",
            "path": "",
            "filename": "mitosis.svg",
            "grade_tags": [],
        },
        {
            "id": "heart",
            "name": "Heart",
            "category": "Human_physiology",
            "author": "test",
            "license": "cc-0",
            "path": "",
            "filename": "heart.svg",
            "grade_tags": [],
        },
    ]
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"total": 4, "icons": icons}))
    return path


@pytest.fixture
def icon_lib(sample_catalog: Path, tmp_path: Path) -> IconLibrary:
    return IconLibrary(catalog_path=sample_catalog, icons_dir=tmp_path / "icons")


class TestIconLibrary:
    def test_get_categories_returns_sorted(self, icon_lib: IconLibrary):
        cats = icon_lib.get_categories()
        assert len(cats) == 3
        names = [c.name for c in cats]
        assert names == ["Cell_types", "Genetics", "Human_physiology"]

    def test_get_icons_all(self, icon_lib: IconLibrary):
        icons, total = icon_lib.get_icons()
        assert total == 4
        assert len(icons) == 4

    def test_get_icons_filter_by_category(self, icon_lib: IconLibrary):
        icons, total = icon_lib.get_icons(category="Genetics")
        assert total == 1
        assert icons[0].id == "dna"

    def test_get_icons_search_name(self, icon_lib: IconLibrary):
        icons, total = icon_lib.get_icons(search="cell")
        assert total == 2

    def test_get_icons_search_id(self, icon_lib: IconLibrary):
        icons, total = icon_lib.get_icons(search="dna")
        assert total == 1
        assert icons[0].name == "Dna"

    def test_get_icons_limit_offset(self, icon_lib: IconLibrary):
        icons, total = icon_lib.get_icons(limit=2, offset=2)
        assert total == 4
        assert len(icons) == 2

    def test_get_icon_by_id_found(self, icon_lib: IconLibrary):
        icon = icon_lib.get_icon_by_id("dna")
        assert icon is not None
        assert icon.name == "Dna"

    def test_get_icon_by_id_not_found(self, icon_lib: IconLibrary):
        icon = icon_lib.get_icon_by_id("nonexistent")
        assert icon is None

    def test_get_icon_svg_not_on_disk(self, icon_lib: IconLibrary):
        svg = icon_lib.get_icon_svg("dna")
        assert svg is None

    def test_get_icon_svg_on_disk(self, icon_lib: IconLibrary, tmp_path: Path):
        icons_dir = tmp_path / "icons"
        cat_dir = icons_dir / "Genetics"
        cat_dir.mkdir(parents=True)
        (cat_dir / "dna.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        svg = icon_lib.get_icon_svg("dna")
        assert svg is not None
        assert "svg" in svg

    def test_get_icon_svg_fallback_author_path(self, icon_lib: IconLibrary, tmp_path: Path):
        icons_dir = tmp_path / "icons"
        cat_dir = icons_dir / "Cell_types"
        cat_dir.mkdir(parents=True)
        (cat_dir / "cell.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        svg = icon_lib.get_icon_svg("cell")
        assert svg is not None


class TestIconLibraryCompose:
    def test_compose_empty_icons(self, icon_lib: IconLibrary):
        svg = icon_lib.compose_from_topic(topic="Biology", icon_ids=[], title="Biology")
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "Biology" in svg

    def test_compose_with_icons(self, icon_lib: IconLibrary):
        svg = icon_lib.compose_from_topic(
            topic="Cell Biology", icon_ids=["dna", "cell"], title="Cell Diagram"
        )
        assert "<svg" in svg
        assert "Cell Diagram" in svg
        assert "Dna" in svg
        assert "Cell" in svg

    def test_compose_with_unknown_icon(self, icon_lib: IconLibrary):
        svg = icon_lib.compose_from_topic(topic="Test", icon_ids=["unknown"])
        assert "<svg" in svg


class TestIconSchemas:
    def test_icon_entry(self):
        entry = IconEntry(id="test", name="Test", category="Test", author="x", license="cc-0")
        assert entry.id == "test"

    def test_icon_category(self):
        cat = IconCategory(name="Genetics", icon_count=10)
        assert cat.icon_count == 10

    def test_icon_list_response(self):
        resp = IconListResponse(
            total=1,
            icons=[IconEntry(id="x", name="X", category="C", author="a", license="cc-0")],
            categories=[IconCategory(name="C", icon_count=1)],
        )
        assert resp.total == 1

    def test_icon_compose_request(self):
        req = IconComposeRequest(topic="DNA", icon_ids=["dna", "cell"])
        assert len(req.icon_ids) == 2

    def test_placed_icon(self):
        pi = PlacedIcon(icon_id="dna", x=10, y=20, label="DNA")
        assert pi.label == "DNA"
        assert pi.x == 10

    def test_icon_compose_response(self):
        resp = IconComposeResponse(diagram_svg="<svg/>", title="Test", topic="Bio", placed_icons=3)
        assert resp.placed_icons == 3
