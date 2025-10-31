"""
Celery Configuration for Background Task Processing
Handles asynchronous PDF indexing, image analysis, and embedding generation
"""

from celery import Celery
from kombu import Queue
import os

from backend.config.settings import settings
from backend.utils import get_logger

logger = get_logger(__name__)

# Initialize Celery app
celery_app = Celery(
    "neurosurgery_kb",
    broker=settings.redis_url,
    backend=settings.redis_url
)

# Celery Configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "backend.services.background_tasks.process_pdf_async": {"queue": "default"},
        "backend.services.background_tasks.extract_text_task": {"queue": "default"},
        "backend.services.background_tasks.extract_images_task": {"queue": "images"},
        "backend.services.background_tasks.analyze_images_task": {"queue": "images"},
        "backend.services.background_tasks.generate_embeddings_task": {"queue": "embeddings"},
        "backend.services.background_tasks.extract_citations_task": {"queue": "default"},
        "backend.services.background_tasks.finalize_pdf_processing": {"queue": "default"},
    },

    # Queue configuration
    task_queues=(
        Queue("default", routing_key="task.#"),
        Queue("images", routing_key="images.#"),
        Queue("embeddings", routing_key="embeddings.#"),
    ),

    # Result backend settings
    result_backend=settings.redis_url,
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,

    # Task execution settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Task behavior
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes max per task
    task_soft_time_limit=1500,  # 25 minutes soft limit
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Retry configuration
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,

    # Worker configuration
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory management)

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Task autodiscovery
celery_app.autodiscover_tasks(["backend.services"])

# IMPORTANT: Explicitly import background_tasks to register all tasks
# This ensures tasks are available when workers start
try:
    from backend.services import background_tasks
    logger.info(f"Background tasks module imported successfully")
except ImportError as e:
    logger.error(f"Failed to import background_tasks: {e}")

logger.info("Celery app configured successfully")


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery configuration"""
    logger.info(f"Request: {self.request!r}")
    return {"status": "ok", "message": "Celery is working!"}
