from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.database import SessionLocal
from app.tasks import run_analysis_task


scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def scheduled_run() -> None:
    db = SessionLocal()
    try:
        run_analysis_task(db)
    finally:
        db.close()


def start_scheduler() -> None:
    settings = get_settings()
    if not scheduler.get_job("daily_amazon_analysis"):
        scheduler.add_job(
            scheduled_run,
            "cron",
            hour=settings.daily_run_hour,
            minute=0,
            id="daily_amazon_analysis",
            replace_existing=True,
        )
    if not scheduler.running:
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
