from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import TaskRun
from app.pagination import paginate_list
from app.tasks import run_analysis_task


router = APIRouter(prefix="/tasks", tags=["tasks"])
templates = Jinja2Templates(directory="app/templates")


def run_in_background() -> None:
    db = SessionLocal()
    try:
        run_analysis_task(db)
    finally:
        db.close()


@router.get("")
def task_runs(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    runs = db.execute(select(TaskRun).order_by(desc(TaskRun.started_at))).scalars().all()
    page_runs, pagination = paginate_list(runs, page, 10, "/tasks")
    return templates.TemplateResponse("task_runs.html", {"request": request, "runs": page_runs, "pagination": pagination})


@router.post("/run")
def manual_run(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_in_background)
    return RedirectResponse("/tasks", status_code=303)
