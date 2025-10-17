from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Any, Dict
import httpx
import re
from urllib.parse import urlparse

from ..utils.extractor import SimpleJobExtractor
from ..utils.advanced_extractor import AdvancedJobExtractor
from ..utils.net import fetch_html
from ..utils.jobposting import standardize_to_jobposting
from ..utils.normalize import normalize_jd_text

router = APIRouter()
extractor = SimpleJobExtractor()
advanced_extractor = AdvancedJobExtractor()


class ExtractRequest(BaseModel):
    url: HttpUrl
def _derive_company_from_url(url: str) -> str | None:
    try:
        u = urlparse(url)
        host = (u.hostname or "").lower()
        if not host:
            return None
        path_parts = [p for p in (u.path or '').split('/') if p]

        # Known ATS patterns: extract org from path when possible
        if host.endswith("lever.co") and path_parts:
            # jobs.lever.co/<org>/...
            org = path_parts[0]
            return re.sub(r"[\-_]+", " ", org).strip().title() or None
        if host.endswith("greenhouse.io") and path_parts:
            # boards.greenhouse.io/<org>/...
            org = path_parts[0]
            return re.sub(r"[\-_]+", " ", org).strip().title() or None

        # Workday and similar: <org>.wdX.myworkdayjobs.com
        m = re.match(r"^([a-z0-9-]+)\.", host)
        sld_candidates = {"www", "jobs", "careers", "boards"}
        if m:
            sub = m.group(1)
            if sub not in sld_candidates:
                name = sub
            else:
                parts = host.split('.')
                name = parts[-2] if len(parts) >= 2 else sub
        else:
            parts = host.split('.')
            name = parts[-2] if len(parts) >= 2 else host

        clean = re.sub(r"[^a-z0-9]+", " ", name).strip()
        return clean.title() if clean else None
    except Exception:
        return None



@router.post("/job")
async def extract_job(body: ExtractRequest) -> Dict[str, Any]:
    """Fetch job page HTML and return structured job data suitable for frontend use."""
    url = str(body.url)
    try:
        html, status = await fetch_html(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fetch failed: {e}")

    lower = html.lower()
    blocked_markers = [
        "access denied", "forbidden", "error 403", "blocked", "are you a robot",
        "captcha", "robot check", "verify you are human", "attention required | cloudflare",
        "something went wrong", "request was denied", "temporarily unavailable"
    ]
    if any(m in lower for m in blocked_markers):
        raise HTTPException(status_code=404, detail="not_found_or_blocked")
    data = extractor.extract(url, html)
    # Fallback company from URL if missing
    if not data.get("company"):
        fallback_company = _derive_company_from_url(url)
        if fallback_company:
            data["company"] = fallback_company
    # Normalize description to plain text with ordered sections
    if data.get("description"):
        try:
            data["description"] = normalize_jd_text(data["description"])
        except Exception:
            pass
    jobposting = standardize_to_jobposting(data)
    return {"success": True, "data": jobposting}


class ExtractFromHtmlRequest(BaseModel):
    url: HttpUrl
    html: str


@router.post("/from-html")
async def extract_from_html(body: ExtractFromHtmlRequest) -> Dict[str, Any]:
    """Extract job data from supplied HTML (HTML fetched by the frontend server)."""
    try:
        data = extractor.extract(str(body.url), body.html)
        if not data.get("company"):
            fallback_company = _derive_company_from_url(str(body.url))
            if fallback_company:
                data["company"] = fallback_company
        if data.get("description"):
            try:
                data["description"] = normalize_jd_text(data["description"])
            except Exception:
                pass
        jobposting = standardize_to_jobposting(data)
        return {"success": True, "data": jobposting}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@router.post("/advanced")
async def extract_advanced(body: ExtractRequest) -> Dict[str, Any]:
    """Enhanced extraction with additional processing."""
    url = str(body.url)
    try:
        html, status = await fetch_html(url)
        if status >= 400:
            return {"success": False, "data": {}, "message": f"Failed to fetch URL: HTTP {status}"}
        
        # Enhanced extraction
        job_data = extractor.extract(url, html)
        if not job_data.get("company"):
            fallback_company = _derive_company_from_url(url)
            if fallback_company:
                job_data["company"] = fallback_company
        if job_data.get("description"):
            try:
                job_data["description"] = normalize_jd_text(job_data["description"])
            except Exception:
                pass
        
        # Additional processing for advanced extraction
        if job_data.get("description"):
            import re
            # Extract more skills
            desc_text = job_data["description"].lower()
            additional_skills = []
            
            skill_patterns = [
                r"\b(?:react|vue|angular|svelte|node\.?js|express|django|flask|fastapi|spring)\b",
                r"\b(?:aws|azure|gcp|docker|kubernetes|jenkins|git|postgresql|mysql|mongodb)\b",
                r"\b(?:python|javascript|typescript|java|c\+\+|c#|go|rust|php|ruby|swift|kotlin)\b",
            ]
            
            for pattern in skill_patterns:
                matches = re.findall(pattern, desc_text, re.IGNORECASE)
                additional_skills.extend(matches)
            
            if additional_skills:
                job_data["additional_skills"] = list(set(additional_skills))
        
        jobposting = standardize_to_jobposting(job_data)
        return {"success": True, "data": jobposting, "message": "Advanced extraction completed successfully"}
    
    except Exception as e:
        return {"success": False, "data": {}, "message": f"Advanced extraction failed: {str(e)}"}


@router.post("/ai")
async def extract_with_ai(body: ExtractRequest) -> Dict[str, Any]:
    """AI-powered dynamic job extraction without static selectors."""
    url = str(body.url)
    try:
        html, status = await fetch_html(url)
        if status >= 400:
            return {"success": False, "data": {}, "message": f"Failed to fetch URL: HTTP {status}"}
        
        # Use AI-powered dynamic extraction
        job_data = extractor.extract(url, html, use_ai=True)
        if not job_data.get("company"):
            fallback_company = _derive_company_from_url(url)
            if fallback_company:
                job_data["company"] = fallback_company
        # Normalize description into clean plain text with ordered sections
        if job_data.get("description"):
            try:
                job_data["description"] = normalize_jd_text(job_data["description"])
            except Exception:
                # Non-fatal; keep raw text if normalization fails
                pass
        jobposting = standardize_to_jobposting(job_data)
        return {"success": True, "data": jobposting, "message": "AI-powered extraction completed successfully"}

    except Exception as e:
        return {"success": False, "data": {}, "message": f"AI extraction failed: {str(e)}"}
