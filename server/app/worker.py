from __future__ import annotations

import asyncio
import os
import sys
import time
import logging
from typing import Dict, Any

import httpx

from .utils.queue import fetch_next_job, fetch_next_job_any, set_job_status, JD_QUEUE_KEY, QUEUE_KEY
from .utils.extractor import SimpleJobExtractor
from .utils.advanced_extractor import AdvancedJobExtractor
from .utils.jobposting import standardize_to_jobposting
from .utils.net import fetch_html
import re


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s [worker] %(levelname)s: %(message)s")


HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def process_job(job: Dict[str, Any]) -> None:
    job_id = job["id"]
    url = job["url"]
    set_job_status(job_id, "running")
    try:
        # Try advanced extraction first (with IP rotation)
        try:
            from .utils.advanced_extractor import extract_job_advanced
            job_data = await extract_job_advanced(url)
            html = "success"  # Placeholder since extraction is complete
            status = 200
        except Exception as e:
            # Fallback to original method
            logging.info(f"Advanced extraction failed, falling back to basic fetch: {e}")
            html, status = await fetch_html(url, timeout=25.0, tries=3)
        if status >= 400:
            set_job_status(job_id, "failed", error=f"http_{status}")
            return

        # Heuristics: detect error/blocked pages (captcha, access denied, generic error)
        lower = html.lower()
        blocked_markers = [
            "access denied", "forbidden", "error 403", "blocked", "are you a robot",
            "captcha", "robot check", "verify you are human", "attention required | cloudflare",
            "something went wrong", "request was denied", "temporarily unavailable"
        ]
        hit = next((m for m in blocked_markers if m in lower), None)
        if hit:
            set_job_status(job_id, "failed", error=f"blocked_or_not_found: {hit} (http {status})")
            return
        simple = SimpleJobExtractor().extract(url, html)
        # If description too short, try advanced for better content extraction
        data = simple
        if not simple.get("description") or len(str(simple.get("description"))) < 120:
            adv = AdvancedJobExtractor().extract(url, html)
            # merge conservatively
            for k in ["title", "company", "location", "description", "skills"]:
                if (not data.get(k)) and adv.get(k):
                    data[k] = adv[k]
        # Prepare artifacts (raw_html + basic cleaned text + standard JobPosting)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        raw_text = soup.get_text('\n', strip=True)
        jobposting = standardize_to_jobposting(data)
        # Minimize immediate data (no big description/skills here; only top-level fields)
        minimal = {
            "title": data.get("title"),
            "company": data.get("company"),
            "location": data.get("location"),
            "source_url": url,
        }
        set_job_status(job_id, "completed", data=minimal, artifacts={
            "raw_html": html,
            "raw_text": raw_text,
            "description": data.get("description") or "",
            "jobposting": jobposting,
            "http_status": status,
        })
    except Exception as e:
        set_job_status(job_id, "failed", error=str(e))


async def process_jd_job(job: Dict[str, Any]) -> None:
    """Process JD analysis job: fetch URL, extract minimal fields, write artifacts to pipeline row."""
    job_id = job.get("id")
    url = job.get("url")
    pipeline_id = job.get("pipeline_id")
    set_job_status(job_id, "running", data={"stage": "queued", "progress": 0})
    
    def _persist_pipeline_jd_failure(pipeline_id: str, err: str, details: Dict[str, Any] | None = None) -> None:
        """Best-effort persist a JD failure state + details into the pipeline row for UI visibility."""
        try:
            from app.models import SessionLocal, PipelineV2Record
            import json
            with SessionLocal() as db:
                row = db.get(PipelineV2Record, pipeline_id)
                if not row:
                    return
                payload = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
                st = payload.get("statuses", {})
                art = payload.get("artifacts", {})
                st["jd"] = "failed"
                art["jd_error"] = err
                if details:
                    # Keep this compact
                    art["jd_error_details"] = {
                        k: v for k, v in details.items() if k in {"http_status", "blocked_marker", "strategy", "stage", "url"}
                    }
                row.statuses_json = json.dumps({"statuses": st, "artifacts": art})
                db.add(row); db.commit(); db.refresh(row)
        except Exception:
            # non-fatal
            pass
    try:
        logging.info(f"JD job {job_id} for pipeline {pipeline_id}: start (url={url})")
        set_job_status(job_id, "running", data={"stage": "extracting(advanced)", "progress": 10})
        # Prefer advanced extractor (uses IP rotation: Tor/free proxies/browser)
        from .utils.advanced_extractor import extract_job_advanced
        from .utils.advanced_fetch import IPRotationManager
        try:
            job_data = await extract_job_advanced(url)
            data = job_data
            logging.info(f"JD job {job_id}: advanced extraction succeeded")
            # Fetch HTML via rotation for artifacts (best-effort)
            try:
                manager = IPRotationManager()
                html, status, blocked = await manager.fetch_with_rotation(url, max_retries=3)
                if blocked:
                    html, status = "", 0
            except Exception:
                html, status = "", 0
        except Exception as e:
            logging.info(f"JD job {job_id}: advanced extraction failed, falling back to basic fetch: {e}")
            set_job_status(job_id, "running", data={"stage": "fetching", "progress": 5})
            html, status = await fetch_html(url, timeout=25.0, tries=3)
            logging.info(f"JD job {job_id}: fetched html (status={status}, bytes={len(html) if html else 0})")
            # Original extraction logic for fallback
            if status >= 400:
                err = f"http_{status}"
                details = {"stage": "fetching", "strategy": "basic", "http_status": status, "url": url}
                set_job_status(job_id, "failed", error=err, data=details, artifacts={"html_snippet": (html or "")[:2000]})
                _persist_pipeline_jd_failure(pipeline_id, err, details)
                logging.info(f"JD job {job_id}: failed http status {status}")
                return
            lower = html.lower()
            blocked_markers = [
                "access denied", "forbidden", "error 403", "blocked", "are you a robot",
                "captcha", "robot check", "verify you are human", "attention required | cloudflare",
                "something went wrong", "request was denied", "temporarily unavailable"
            ]
            hit = next((m for m in blocked_markers if m in lower), None)
            if hit:
                logging.info(f"JD job {job_id}: blocked marker detected -> {hit}; attempting anti-bot provider")
                try:
                    set_job_status(job_id, "running", data={"stage": "fetching(antibot)", "progress": 10})
                    from .utils.free_antibot import fetch_html_antibot_free
                    html2, status2 = await fetch_html_antibot_free(url)
                    lower2 = (html2 or '').lower()
                    hit2 = next((m for m in blocked_markers if m in lower2), None)
                    if status2 == 200 and not hit2 and html2:
                        html, status = html2, status2
                        logging.info(f"JD job {job_id}: free anti-bot fetch succeeded (status={status2})")
                    else:
                        err = f"blocked_or_not_found: {hit or hit2 or 'blocked'} (http {status2})"
                        details = {
                            "stage": "fetching(antibot)",
                            "strategy": "free_antibot",
                            "blocked_marker": hit2 or hit,
                            "http_status": status2,
                            "url": url,
                        }
                        set_job_status(job_id, "failed", error=err, data=details, artifacts={"html_snippet": (html2 or html or "")[:2000]})
                        _persist_pipeline_jd_failure(pipeline_id, err, details)
                        logging.info(f"JD job {job_id}: free anti-bot failed -> {hit2} (status={status2})")
                        return
                except Exception as e:
                    err = f"blocked_or_not_found: {hit} (http {status}); antibot_error: {e}"
                    details = {
                        "stage": "fetching(antibot)",
                        "strategy": "free_antibot",
                        "blocked_marker": hit,
                        "http_status": status,
                        "url": url,
                    }
                    set_job_status(job_id, "failed", error=err, data=details, artifacts={"html_snippet": (html or "")[:2000]})
                    _persist_pipeline_jd_failure(pipeline_id, err, details)
                    logging.info(f"JD job {job_id}: free anti-bot exception -> {e}")
                    return
            set_job_status(job_id, "running", data={"stage": "extracting", "progress": 25})
            simple = SimpleJobExtractor().extract(url, html)
            data = simple
            if not simple.get("description") or len(str(simple.get("description"))) < 120:
                set_job_status(job_id, "running", data={"stage": "extracting+advanced", "progress": 50})
                adv = AdvancedJobExtractor().extract(url, html)
                for k in ["title", "company", "location", "description", "skills"]:
                    if (not data.get(k)) and adv.get(k):
                        data[k] = adv[k]
        from bs4 import BeautifulSoup
        from app.utils.normalize import normalize_jd_text
        soup = BeautifulSoup(html, 'html.parser')
        raw_text = soup.get_text('\n', strip=True)
        desc = data.get("description") or ""
        set_job_status(job_id, "running", data={"stage": "normalizing", "progress": 70})
        try:
            desc = normalize_jd_text(desc)
        except Exception:
            pass
        minimal = {
            "title": data.get("title"),
            "company": data.get("company"),
            "location": data.get("location"),
            "source_url": url,
        }
        set_job_status(job_id, "running", data={"stage": "persisting", "progress": 85})
        set_job_status(job_id, "completed", data=minimal, artifacts={
            "raw_html": html,
            "raw_text": raw_text,
            "description": desc or (data.get("description") or ""),
            "http_status": status,
        })
        logging.info(f"JD job {job_id}: completed extraction and artifacts prepared")
        # Persist into pipeline.artifacts.jd and set statuses.jd/profile
        try:
            from app.models import SessionLocal, PipelineV2Record
            import json
            with SessionLocal() as db:
                row = db.get(PipelineV2Record, pipeline_id)
                if row:
                    payload = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
                    st = payload.get("statuses", {})
                    art = payload.get("artifacts", {})
                    jd_art = {
                        "url": url,
                        "title": minimal.get("title") or row.name,
                        "company": minimal.get("company") or row.company,
                        "description": desc or (data.get("description") or ""),
                    }
                    art["jd"] = jd_art
                    st["jd"] = "complete" if jd_art.get("description") else "pending"
                    st.setdefault("profile", "complete")
                    row.name = jd_art.get("title") or row.name
                    row.company = jd_art.get("company") or row.company
                    row.statuses_json = json.dumps({"statuses": st, "artifacts": art})
                    db.add(row); db.commit(); db.refresh(row)
                    logging.info(f"JD job {job_id}: persisted into pipeline {pipeline_id}; status jd={st['jd']}")
        except Exception:
            # non-fatal: artifacts are still in Redis job
            pass
    except Exception as e:
        set_job_status(job_id, "failed", error=str(e))
        # Also persist failure on the pipeline so SSE and UI can reflect it
        try:
            from app.models import SessionLocal, PipelineV2Record
            import json
            with SessionLocal() as db:
                row = db.get(PipelineV2Record, pipeline_id)
                if row:
                    payload = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
                    st = payload.get("statuses", {})
                    art = payload.get("artifacts", {})
                    st["jd"] = "failed"
                    art.setdefault("jd_error", str(e))
                    row.statuses_json = json.dumps({"statuses": st, "artifacts": art})
                    db.add(row); db.commit(); db.refresh(row)
            logging.info(f"JD job {job_id}: exception -> {e}")
        except Exception:
            pass


async def main() -> None:
    while True:
        job = fetch_next_job_any([JD_QUEUE_KEY, QUEUE_KEY], timeout=5)
        if not job:
            await asyncio.sleep(0.5)
            continue
        q = job.get("_queue")
        if q == JD_QUEUE_KEY:
            await process_jd_job(job)
        else:
            await process_job(job)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
