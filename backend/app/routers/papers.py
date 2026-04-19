from pathlib import Path
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db, SessionLocal
from app.models import Paper
from app.schemas import PaperCreate, PaperListItem, PaperDetail, ProcessingStatus
from app.services.arxiv_service import arxiv_service
from app.config import settings

router = APIRouter()


def _extract_arxiv_id(url: str) -> str:
    from urllib.parse import urlparse
    url = url.strip()
    if "arxiv.org" in url:
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        return parts[-1]
    return url


def process_paper_task(arxiv_id: str):
    """Background task to download and process paper."""
    db = SessionLocal()
    try:
        paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
        if not paper:
            return
        
        paper.status = "processing"
        db.commit()
        
        result = arxiv_service.process_paper(arxiv_id)
        
        paper.title = result.get("title", "")
        paper.title_zh = result.get("title_zh", "")
        paper.authors = result.get("authors", "")
        paper.abstract = result.get("abstract", "")
        paper.report_md = result.get("report_md", "")
        paper.raw_sections = result.get("raw_sections", [])
        paper.images = result.get("images", [])
        paper.status = result.get("status", "failed")
        paper.error_msg = result.get("error_msg")
        db.commit()
    except Exception as e:
        db.rollback()
        paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
        if paper:
            paper.status = "failed"
            paper.error_msg = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/", response_model=ProcessingStatus)
def create_paper(
    payload: PaperCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    arxiv_id = _extract_arxiv_id(payload.arxiv_url)
    
    # Check existing
    existing = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
    if existing:
        return ProcessingStatus(
            arxiv_id=arxiv_id,
            status=existing.status,
            message=f"Paper already exists. Status: {existing.status}",
        )
    
    # Create pending record
    new_paper = Paper(arxiv_id=arxiv_id, status="pending")
    db.add(new_paper)
    db.commit()
    
    # Start background processing
    background_tasks.add_task(process_paper_task, arxiv_id)
    
    return ProcessingStatus(
        arxiv_id=arxiv_id,
        status="pending",
        message="Paper submitted for processing",
    )


@router.get("/", response_model=List[PaperListItem])
def list_papers(
    q: Optional[str] = Query(None, description="Search title or arxiv_id"),
    db: Session = Depends(get_db),
):
    query = db.query(Paper).order_by(Paper.created_at.desc())
    if q:
        query = query.filter(
            (Paper.title.ilike(f"%{q}%")) |
            (Paper.title_zh.ilike(f"%{q}%")) |
            (Paper.arxiv_id.ilike(f"%{q}%"))
        )
    return query.all()


@router.get("/{arxiv_id}", response_model=PaperDetail)
def get_paper(arxiv_id: str, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.delete("/{arxiv_id}")
def delete_paper(arxiv_id: str, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Delete images
    import shutil
    img_dir = Path(settings.images_dir) / arxiv_id
    if img_dir.exists():
        shutil.rmtree(img_dir)
    
    # Delete LaTeX source
    latex_dir = Path(settings.latex_dir) / arxiv_id
    if latex_dir.exists():
        shutil.rmtree(latex_dir)
    
    db.delete(paper)
    db.commit()
    return {"message": "Paper deleted"}


@router.post("/{arxiv_id}/retry")
def retry_paper(arxiv_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    paper.status = "pending"
    paper.error_msg = None
    db.commit()
    
    background_tasks.add_task(process_paper_task, arxiv_id)
    return ProcessingStatus(arxiv_id=arxiv_id, status="pending", message="Retrying processing")
