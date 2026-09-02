from celery import Celery
import os

broker = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "cybersec_scraper",
    broker=broker,
    backend=backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    imports=("tasks.scrape_tasks",),
    broker_connection_retry_on_startup=True,
)

@celery_app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
