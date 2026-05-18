from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Keyword
from app.opportunity import expand_keyword


router = APIRouter(prefix="/keywords", tags=["keywords"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def list_keywords(request: Request, db: Session = Depends(get_db)):
    keywords = db.execute(select(Keyword).order_by(Keyword.id.desc())).scalars().all()
    return templates.TemplateResponse("keywords.html", {"request": request, "keywords": keywords})


@router.post("")
def create_keyword(
    keyword: str = Form(...),
    category: str = Form(""),
    priority: str = Form("中"),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    exists = db.execute(select(Keyword).where(Keyword.keyword == keyword.strip())).scalar_one_or_none()
    if not exists:
        db.add(Keyword(keyword=keyword.strip(), category=category, priority=priority, status=status))
        db.commit()
    return RedirectResponse("/keywords", status_code=303)


@router.post("/expand")
def expand_keywords(
    base_keyword: str = Form(...),
    category: str = Form("五金工具"),
    priority: str = Form("中"),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    existing = {row[0] for row in db.execute(select(Keyword.keyword)).all()}
    for keyword in expand_keyword(base_keyword):
        if keyword not in existing:
            db.add(Keyword(keyword=keyword, category=category, priority=priority, status=status))
            existing.add(keyword)
    db.commit()
    return RedirectResponse("/keywords", status_code=303)


@router.post("/{keyword_id}/status")
def update_status(keyword_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    item = db.get(Keyword, keyword_id)
    if item:
        item.status = status
        db.commit()
    return RedirectResponse("/keywords", status_code=303)


@router.post("/{keyword_id}/delete")
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    item = db.get(Keyword, keyword_id)
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/keywords", status_code=303)
