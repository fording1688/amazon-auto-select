from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import SessionLocal, init_db
from app.routes import copilot, keywords, operations, products, reports, research, tasks
from app.scheduler import start_scheduler, stop_scheduler
from app.report_importer import ensure_report_dirs
from app.tasks import seed_keywords


app = FastAPI(title="亚马逊自动测款分析系统")
templates = Jinja2Templates(directory="app/templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(copilot.router)
app.include_router(keywords.router)
app.include_router(operations.router)
app.include_router(products.router)
app.include_router(reports.router)
app.include_router(research.router)
app.include_router(tasks.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    ensure_report_dirs()
    db = SessionLocal()
    try:
        seed_keywords(db)
    finally:
        db.close()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/")
def home(request: Request):
    return RedirectResponse(url="/products")
