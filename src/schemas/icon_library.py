from typing import Optional

from src.schemas.base import SchemaModel


class IconEntry(SchemaModel):
    id: str
    name: str
    category: str
    author: str
    license: str
    filename: str = ""
    grade_tags: list[int] = []


class IconCategory(SchemaModel):
    name: str
    icon_count: int


class IconListResponse(SchemaModel):
    total: int
    icons: list[IconEntry]
    categories: list[IconCategory]


class IconComposeRequest(SchemaModel):
    topic: str
    icon_ids: list[str]
    layout: str = "grid"
    title: Optional[str] = None


class PlacedIcon(SchemaModel):
    icon_id: str
    x: float
    y: float
    width: float = 80
    height: float = 80
    label: Optional[str] = None


class IconComposeRequestCustom(SchemaModel):
    topic: str
    icons: list[PlacedIcon]
    title: Optional[str] = None


class IconComposeResponse(SchemaModel):
    diagram_svg: str
    title: str
    topic: str
    placed_icons: int
