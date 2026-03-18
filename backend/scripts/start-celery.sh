#!/bin/bash

echo "启动Celery Worker..."

cd /app

celery -A app.celery_config worker \
    --loglevel=info \
    --concurrency=2 \
    --max-tasks-per-child=50 \
    --time-limit=3600 \
    --soft-time-limit=3000