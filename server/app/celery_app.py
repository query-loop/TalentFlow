from __future__ import annotations

import os
try:
    from celery import Celery

    # Prefer explicit CELERY_* env vars, fallback to REDIS_URL if present, then to localhost defaults
    REDIS_URL = os.environ.get("CELERY_BROKER_URL") or os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    # Result backend: prefer CELERY_RESULT_BACKEND, fallback to same redis host but DB=1
    default_backend = None
    try:
        # if REDIS_URL ends with /<db>, use same host but DB=1 for results
        if REDIS_URL.rsplit('/', 1)[-1].isdigit():
            base = REDIS_URL.rsplit('/', 1)[0]
            default_backend = f"{base}/1"
    except Exception:
        default_backend = "redis://localhost:6379/1"
    BACKEND = os.environ.get("CELERY_RESULT_BACKEND") or default_backend or "redis://localhost:6379/1"

    # Ensure tasks module is included so workers register tasks on startup
    celery_app = Celery("talentflow", broker=REDIS_URL, backend=BACKEND, include=["app.tasks"])
    celery_app.conf.update(task_track_started=True)

    def get_celery_app() -> Celery:
        return celery_app

    # Ensure tasks are imported and registered when the celery app module is imported by the worker.
    try:
        # Importing here avoids a circular import at module import time because tasks import celery_app.
        import importlib, traceback, sys
        importlib.import_module("app.tasks")
    except Exception as e:
        # Log import failure to stdout so workers show why tasks weren't registered
        try:
            sys.stdout.write("[celery_app] failed to import app.tasks: " + repr(e) + "\n")
            traceback.print_exc(file=sys.stdout)
        except Exception:
            pass

except Exception:
    # Celery not installed in the test environment — provide a lightweight shim so imports work
    class _DummyAsyncResult:
        def __init__(self, id: str):
            self.id = id
            self.state = None

    class _DummyCeleryApp:
        def task(self, bind=False):
            # decorator that returns the function unchanged
            def _decorator(fn):
                return fn
            return _decorator

        def AsyncResult(self, id: str):
            return _DummyAsyncResult(id)

    celery_app = _DummyCeleryApp()

    def get_celery_app():
        return celery_app
