from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.keyword_research import loads, run_keyword_research
from app.models import Keyword, KeywordResearchRun


router = APIRouter(prefix="/research", tags=["research"])
templates = Jinja2Templates(directory="app/templates")


def _view_model(run: KeywordResearchRun | None) -> dict:
    if not run:
        return {}
    return {
        "run": run,
        "expanded_keywords": loads(run.expanded_keywords_json, []),
        "product_terms": loads(run.product_terms_json, []),
        "modifier_terms": loads(run.modifier_terms_json, []),
        "ad_keywords": loads(run.ad_keywords_json, []),
        "negative_keywords": loads(run.negative_keywords_json, []),
        "raw_titles": loads(run.raw_titles_json, []),
    }


@router.get("")
def research_page(request: Request, db: Session = Depends(get_db)):
    runs = db.execute(select(KeywordResearchRun).order_by(desc(KeywordResearchRun.created_at)).limit(20)).scalars().all()
    latest = runs[0] if runs else None
    return templates.TemplateResponse(
        "research.html",
        {"request": request, "runs": runs, **_view_model(latest)},
    )


@router.get("/{run_id}")
def research_detail(run_id: int, request: Request, db: Session = Depends(get_db)):
    runs = db.execute(select(KeywordResearchRun).order_by(desc(KeywordResearchRun.created_at)).limit(20)).scalars().all()
    run = db.get(KeywordResearchRun, run_id)
    return templates.TemplateResponse(
        "research.html",
        {"request": request, "runs": runs, **_view_model(run)},
    )


@router.post("")
def create_research(seed_keyword: str = Form(...), db: Session = Depends(get_db)):
    run = run_keyword_research(db, seed_keyword.strip())
    return RedirectResponse(f"/research/{run.id}", status_code=303)


@router.post("/{run_id}/add-keywords")
def add_research_keywords(
    run_id: int,
    selected_keywords: list[str] = Form([]),
    category: str = Form("五金工具"),
    priority: str = Form("中"),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    existing = {row[0] for row in db.execute(select(Keyword.keyword)).all()}
    for keyword in selected_keywords:
        normalized = " ".join(keyword.lower().strip().split())
        if normalized and normalized not in existing:
            db.add(Keyword(keyword=normalized, category=category, priority=priority, status=status))
            existing.add(normalized)
    db.commit()
    return RedirectResponse(f"/research/{run_id}", status_code=303)
