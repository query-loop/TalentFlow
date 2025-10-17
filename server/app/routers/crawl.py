from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx

from ..utils.queue import enqueue_crawl, get_job


router = APIRouter()


class SubmitRequest(BaseModel):
    url: HttpUrl
    meta: Optional[Dict[str, Any]] = None


@router.post("/submit")
async def submit(body: SubmitRequest) -> Dict[str, Any]:
    try:
        job_id = enqueue_crawl(str(body.url), body.meta)
        return {"success": True, "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue: {e}")


@router.get("/status/{job_id}")
async def status(job_id: str) -> Dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Redact large fields from status; provide has_artifacts flag
    job_out: Dict[str, Any] = {k: job.get(k) for k in ("id","status","created_at","updated_at","meta") if k in job}
    data = job.get("data") or {}
    # Only include minimal fields in data
    job_out["data"] = {k: data.get(k) for k in ("title","company","location","source_url") if k in data}
    job_out["error"] = job.get("error")
    job_out["has_artifacts"] = bool(job.get("artifacts"))
    return {"success": True, "job": job_out}


@router.get("/artifact/{job_id}")
async def artifact(job_id: str) -> Dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    arts = job.get("artifacts") or {}
    return {"success": True, "artifacts": {
        "raw_html": arts.get("raw_html") or "",
        "raw_text": arts.get("raw_text") or "",
        "description": arts.get("description") or "",
    }}
