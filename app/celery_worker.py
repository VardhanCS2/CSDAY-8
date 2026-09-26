from celery import Celery


celery_app = Celery(
    "task_management",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)


celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
)


# Register Celery tasks
celery_app.conf.imports = (
    "app.tasks.background_tasks",
)