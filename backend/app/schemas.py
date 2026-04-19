from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PaperCreate(BaseModel):
    arxiv_url: str = Field(..., description="ArXiv URL or ID, e.g., 2405.12345 or https://arxiv.org/abs/2405.12345")


class PaperBase(BaseModel):
    arxiv_id: str
    title: Optional[str] = None
    title_zh: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    status: str = "pending"
    error_msg: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaperListItem(PaperBase):
    id: int


class PaperDetail(PaperBase):
    id: int
    report_md: Optional[str] = None
    raw_sections: Optional[List[Dict[str, Any]]] = None
    images: Optional[List[str]] = None


class ProcessingStatus(BaseModel):
    arxiv_id: str
    status: str
    message: Optional[str] = None
