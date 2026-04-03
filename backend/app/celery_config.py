from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from app.core.config import settings
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

celery_app = Celery(
    "legal_rag_tasks",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    include=[
        "app.tasks.document_tasks",
        "app.tasks.graph_tasks"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


def _setup_celery_file_logging(logger, **kwargs):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    file_handler = RotatingFileHandler(
        log_dir / "celery.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    error_handler = RotatingFileHandler(
        log_dir / "celery_error.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    print(f"[Celery] 日志已配置: {log_dir / 'celery.log'}")


@after_setup_logger.connect
def setup_logger(logger, **kwargs):
    _setup_celery_file_logging(logger, **kwargs)


@after_setup_task_logger.connect
def setup_task_logger(logger, **kwargs):
    _setup_celery_file_logging(logger, **kwargs)