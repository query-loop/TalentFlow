from __future__ import annotations

import os
try:
    from celery import Celery

    REDIS_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    celery_app = Celery("talentflow", broker=REDIS_URL, backend=BACKEND)
    celery_app.conf.update(task_track_started=True)

    def get_celery_app() -> Celery:
        return celery_app

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
