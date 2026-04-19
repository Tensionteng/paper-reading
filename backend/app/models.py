from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    arxiv_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=True)
    title_zh = Column(String, nullable=True)
    authors = Column(String, nullable=True)
    abstract = Column(Text, nullable=True)
    report_md = Column(Text, nullable=True)       # LLM generated structured report
    raw_sections = Column(JSON, nullable=True)    # Original LaTeX parsed sections
    images = Column(JSON, default=list)           # List of image relative paths
    status = Column(String, default="pending")    # pending/processing/done/failed
    error_msg = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
