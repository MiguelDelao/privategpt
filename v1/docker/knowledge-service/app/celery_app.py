"""
Celery Application for Async Document Processing
Handles background tasks with Redis as broker
"""

import os
from celery import Celery

# Initialize Celery app
celery_app = Celery(
    "knowledge_service",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    include=["app.tasks.document_tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "app.tasks.document_tasks.process_document_async": {"queue": "documents"},
        "app.tasks.document_tasks.update_progress": {"queue": "progress"}
    },
    
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task timeouts and retries
    task_soft_time_limit=600,  # 10 minutes
    task_time_limit=900,       # 15 minutes
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Progress tracking
    task_track_started=True,
    result_expires=3600,  # 1 hour
    
    # Worker configuration
    worker_max_tasks_per_child=50,
    worker_disable_rate_limits=True,
) 