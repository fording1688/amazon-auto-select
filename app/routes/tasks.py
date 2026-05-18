from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import TaskRun
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
def task_runs(request: Request, db: Session = Depends(get_db)):
    runs = db.execute(select(TaskRun).order_by(desc(TaskRun.started_at)).limit(30)).scalars().all()
    return templates.TemplateResponse("task_runs.html", {"request": request, "runs": runs})


@router.post("/run")
def manual_run(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_in_background)
    return RedirectResponse("/tasks", status_code=303)
