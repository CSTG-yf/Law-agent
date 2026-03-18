@echo off
echo Starting Celery Worker...

cd /d %~dp0\..

uv run celery -A app.celery_config worker ^
    --loglevel=info ^
    --pool=solo ^
    --concurrency=1

pause