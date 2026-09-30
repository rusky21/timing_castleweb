from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.domain.entities import CaseCategory


class TagSchema(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class CaseListItem(BaseModel):
    id: int
    slug: str
    title: str
    client_name: str
    year: int
    category: CaseCategory
    short_description: str
    results_summary: str
    metrics: Dict[str, Any]
    cover_image: Optional[str] = None
    is_featured: bool
    tags: List[TagSchema]

    model_config = ConfigDict(from_attributes=True)


class CaseDetail(CaseListItem):
    problem: str
    solution_fe: str
    solution_be: str
    live_url: Optional[str] = None
    gallery_images: List[str]
    client_review: Optional[str] = None
    client_author: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
