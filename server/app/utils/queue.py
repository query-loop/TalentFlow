from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, Optional

import redis


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = "tf:crawl:queue"
JOB_PREFIX = "tf:crawl:job:"

# JD analysis queue (pipeline job)
JD_QUEUE_KEY = "tf:jd:queue"
JD_JOB_PREFIX = "tf:jd:job:"


def get_client() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)


def new_job_id() -> str:
    return uuid.uuid4().hex


def enqueue_crawl(url: str, meta: Optional[Dict[str, Any]] = None) -> str:
    job_id = new_job_id()
    payload = {
        "id": job_id,
        "url": url,
        "status": "queued",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "meta": meta or {},
    }
    r = get_client()
    r.set(JOB_PREFIX + job_id, json.dumps(payload))
    r.rpush(QUEUE_KEY, job_id)
    return job_id


def enqueue_jd_analysis(pipeline_id: str, url: str) -> str:
    """Enqueue a JD analysis job for a pipeline.
    Stores minimal payload in Redis and pushes to JD queue.
    """
    job_id = new_job_id()
    payload = {
        "id": job_id,
        "pipeline_id": pipeline_id,
        "url": url,
        "status": "queued",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    r = get_client()
    r.set(JD_JOB_PREFIX + job_id, json.dumps(payload))
    r.rpush(JD_QUEUE_KEY, job_id)
    return job_id


def fetch_next_job(block: bool = True, timeout: int = 5) -> Optional[Dict[str, Any]]:
    r = get_client()
    if block:
        res = r.blpop(QUEUE_KEY, timeout=timeout)
        if not res:
            return None
        _, job_id = res
    else:
        job_id = r.lpop(QUEUE_KEY)
        if not job_id:
            return None
    raw = r.get(JOB_PREFIX + job_id)
    if not raw:
        return None
    return json.loads(raw)


def fetch_next_job_any(keys: list[str], timeout: int = 5) -> Optional[Dict[str, Any]]:
    """Block-pop from any of the given queues; return job payload with a _queue field indicating source queue.
    Keys must be Redis list keys.
    """
    r = get_client()
    res = r.blpop(keys, timeout=timeout)
    if not res:
        return None
    q_key, job_id = res
    # Determine job prefix by queue
    if q_key == JD_QUEUE_KEY:
        raw = r.get(JD_JOB_PREFIX + job_id)
    else:
        raw = r.get(JOB_PREFIX + job_id)
    job = json.loads(raw) if raw else {"id": job_id}
    job["_queue"] = q_key
    return job


def set_job_status(job_id: str, status: str, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None, artifacts: Optional[Dict[str, Any]] = None) -> None:
    r = get_client()
    # Try JD job first, then crawl
    raw = r.get(JD_JOB_PREFIX + job_id)
    jd = True if raw else False
    if not raw:
        raw = r.get(JOB_PREFIX + job_id)
    job = json.loads(raw) if raw else {"id": job_id}
    job["status"] = status
    job["updated_at"] = int(time.time())
    if data is not None:
        job["data"] = data
    if error is not None:
        job["error"] = error
    if artifacts is not None:
        job["artifacts"] = artifacts
    if jd:
        r.set(JD_JOB_PREFIX + job_id, json.dumps(job))
    else:
        r.set(JOB_PREFIX + job_id, json.dumps(job))


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    r = get_client()
    raw = r.get(JD_JOB_PREFIX + job_id)
    if not raw:
        raw = r.get(JOB_PREFIX + job_id)
    return json.loads(raw) if raw else None
