from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Tuple, Any
from app.models import SessionLocal, PipelineV2Record, Pipeline as LegacyPipeline
from sqlalchemy import select
from cachetools import TTLCache
import json, time, uuid, re, logging
from app.utils.net import fetch_html
from app.utils.extractor import SimpleJobExtractor
from app.utils.normalize import normalize_jd_text
from app.utils.queue import enqueue_jd_analysis, get_job, get_client, JD_QUEUE_KEY
from app.utils.advanced_fetch import IPRotationManager
from app.utils.antibot import antibot
from app.utils.stealth_browser import stealth_browser
import asyncio
from app import ingest as ingest_module
from app.agents.parser_agent import extract_profile_from_text
from app.agents.skill_normalizer import normalize_skills
from app.agents.resume_generator import generate_resume
from app.agents.bullet_optimizer import optimize_experience_bullets
from app.agents.ats_formatter import format_txt, format_docx
from app.agents.scorer import score_profile
from app.utils.fetcher import fetch_text
from app.chroma_client import ChromaClient

router = APIRouter()
logger = logging.getLogger(__name__)

class EnhancedJDExtractor:
    """
    Enhanced JD extraction with comprehensive anti-bot capabilities for Pipeline V2.
    """
    
    def __init__(self):
        self.ip_manager = IPRotationManager()
        self.extraction_stats = {
            "total_attempts": 0,
            "successful_extractions": 0,
            "blocked_attempts": 0,
            "fallback_used": 0,
            "browser_automation_used": 0
        }
    
    async def extract_with_antibot(self, url: str, pipeline_id: str = None) -> Dict[str, Any]:
        """
        Extract JD with comprehensive anti-bot protection and intelligent fallback.
        """
        self.extraction_stats["total_attempts"] += 1
        
        try:
            logger.info(f"Starting enhanced JD extraction for pipeline {pipeline_id}: {url}")
            
            # Step 1: Try advanced extraction with IP rotation
            try:
                from app.utils.advanced_extractor import extract_job_advanced
                result = await extract_job_advanced(url, max_retries=3)
                
                # Validate extraction quality
                if self._is_quality_extraction(result):
                    self.extraction_stats["successful_extractions"] += 1
                    logger.info(f"✅ Advanced extraction successful for {pipeline_id}")
                    return self._format_extraction_result(result, url, "advanced")
                else:
                    logger.warning(f"Advanced extraction returned low-quality data for {pipeline_id}")
                    
            except Exception as e:
                logger.warning(f"Advanced extraction failed for {pipeline_id}: {e}")
                
            # Step 2: Try direct fetch with anti-bot measures
            html, status, blocked_reason = await self.ip_manager.fetch_with_rotation(url, max_retries=2)
            
            if blocked_reason:
                self.extraction_stats["blocked_attempts"] += 1
                logger.warning(f"🚫 Direct fetch blocked for {pipeline_id}: {blocked_reason}")
                
                # Step 3: Try stealth browser as fallback
                return await self._try_stealth_browser_extraction(url, pipeline_id)
            
            if html and status == 200:
                # Extract using simple extractor with enhanced data
                result = SimpleJobExtractor().extract(url, html)
                result = self._enhance_extraction_data(result, html, url)
                
                if self._is_quality_extraction(result):
                    self.extraction_stats["successful_extractions"] += 1
                    logger.info(f"✅ Direct extraction successful for {pipeline_id}")
                    return self._format_extraction_result(result, url, "direct")
            
            # Step 4: Final fallback to stealth browser
            logger.info(f"🔄 Using stealth browser fallback for {pipeline_id}")
            return await self._try_stealth_browser_extraction(url, pipeline_id)
            
        except Exception as e:
            logger.error(f"❌ All extraction methods failed for {pipeline_id}: {e}")
            return self._format_error_result(str(e), url)
    
    async def _try_stealth_browser_extraction(self, url: str, pipeline_id: str = None) -> Dict[str, Any]:
        """Try extraction using stealth browser automation."""
        try:
            self.extraction_stats["browser_automation_used"] += 1
            logger.info(f"🤖 Attempting stealth browser extraction for {pipeline_id}")
            
            # Check if domain is known to have challenges
            domain = url.split('/')[2] if url.startswith('http') else url
            if antibot.is_domain_blocked(domain) or 'cloudflare' in url.lower():
                html, status = await stealth_browser.solve_cloudflare_challenge(url)
            else:
                html, status = await stealth_browser.fetch_with_browser(url)
            
            if html and len(html) > 1000:
                result = SimpleJobExtractor().extract(url, html)
                result = self._enhance_extraction_data(result, html, url)
                
                if self._is_quality_extraction(result):
                    self.extraction_stats["successful_extractions"] += 1
                    logger.info(f"✅ Stealth browser extraction successful for {pipeline_id}")
                    return self._format_extraction_result(result, url, "stealth_browser")
            
            logger.warning(f"Stealth browser returned insufficient content for {pipeline_id}")
            return self._format_error_result("Stealth browser extraction failed", url)
            
        except Exception as e:
            logger.error(f"Stealth browser extraction failed for {pipeline_id}: {e}")
            return self._format_error_result(f"Browser automation failed: {e}", url)
    
    def _is_quality_extraction(self, result: Dict[str, Any]) -> bool:
        """Check if extraction result meets quality standards."""
        if not result:
            return False
        
        description = result.get("description", "")
        title = result.get("title", "")
        
        # Quality checks
        has_title = bool(title and len(title.strip()) > 3)
        has_description = bool(description and len(description.strip()) > 100)
        not_error_page = not any(marker in description.lower() for marker in [
            "access denied", "error 404", "page not found", "blocked", 
            "captcha", "cloudflare", "checking your browser"
        ])
        
        return has_title and has_description and not_error_page
    
    def _enhance_extraction_data(self, result: Dict[str, Any], html: str, url: str) -> Dict[str, Any]:
        """Enhance extraction with additional data parsing."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to extract additional metadata
            if not result.get("company"):
                # Look for company in various places
                company_selectors = [
                    'meta[property="og:site_name"]',
                    '[data-company]', '.company-name', '.employer',
                    'h1', 'title'
                ]
                for selector in company_selectors:
                    elem = soup.select_one(selector)
                    if elem:
                        company = elem.get('content') or elem.get_text()
                        if company and len(company.strip()) > 2:
                            result["company"] = company.strip()
                            break
            
            # Enhance location data
            if not result.get("location"):
                location_selectors = [
                    '[data-location]', '.location', '.job-location',
                    'meta[property="job:location"]'
                ]
                for selector in location_selectors:
                    elem = soup.select_one(selector)
                    if elem:
                        location = elem.get('content') or elem.get_text()
                        if location and len(location.strip()) > 2:
                            result["location"] = location.strip()
                            break
            
            # Add extraction metadata
            result["extraction_metadata"] = {
                "html_length": len(html),
                "extraction_time": time.time(),
                "has_structured_data": bool(soup.find('script', type='application/ld+json')),
                "source_domain": url.split('/')[2] if url.startswith('http') else url
            }
            
        except Exception as e:
            logger.warning(f"Failed to enhance extraction data: {e}")
        
        return result
    
    def _format_extraction_result(self, result: Dict[str, Any], url: str, method: str) -> Dict[str, Any]:
        """Format successful extraction result with metadata."""
        return {
            "success": True,
            "data": result,
            "extraction_method": method,
            "url": url,
            "timestamp": time.time(),
            "quality_score": self._calculate_quality_score(result)
        }
    
    def _format_error_result(self, error: str, url: str) -> Dict[str, Any]:
        """Format error result."""
        return {
            "success": False,
            "error": error,
            "url": url,
            "timestamp": time.time(),
            "extraction_method": "failed"
        }
    
    def _calculate_quality_score(self, result: Dict[str, Any]) -> float:
        """Calculate quality score for extraction (0.0 to 1.0)."""
        score = 0.0
        
        # Title quality (0.2 max)
        title = result.get("title", "")
        if title and len(title) > 5:
            score += 0.2
        
        # Description quality (0.4 max)
        desc = result.get("description", "")
        if desc:
            if len(desc) > 500:
                score += 0.4
            elif len(desc) > 200:
                score += 0.3
            elif len(desc) > 100:
                score += 0.2
        
        # Company info (0.1 max)
        if result.get("company"):
            score += 0.1
        
        # Location info (0.1 max)
        if result.get("location"):
            score += 0.1
        
        # Structured data bonus (0.1 max)
        if result.get("extraction_metadata", {}).get("has_structured_data"):
            score += 0.1
        
        # Requirements detection (0.1 max)
        if desc and any(req in desc.lower() for req in ["required", "must have", "experience", "skills"]):
            score += 0.1
        
        return min(score, 1.0)
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        stats = self.extraction_stats.copy()
        if stats["total_attempts"] > 0:
            stats["success_rate"] = stats["successful_extractions"] / stats["total_attempts"]
            stats["block_rate"] = stats["blocked_attempts"] / stats["total_attempts"]
        else:
            stats["success_rate"] = 0.0
            stats["block_rate"] = 0.0
        
        return stats

# Global enhanced extractor instance
enhanced_extractor = EnhancedJDExtractor()

class V2Statuses(BaseModel):
    intake: str
    jd: str
    profile: str
    gaps: str
    differentiators: str
    draft: str
    compliance: str
    ats: str
    benchmark: str
    actions: str
    export: str

class PipelineV2(BaseModel):
    id: str
    name: str
    createdAt: int
    company: Optional[str] = None
    jdId: Optional[str] = None
    resumeId: Optional[str] = None
    statuses: V2Statuses
    artifacts: Optional[Dict[str, object]] = None

class PipelineV2Create(BaseModel):
    name: str
    company: Optional[str] = None
    jdId: Optional[str] = None
    resumeId: Optional[str] = None

class PipelineV2Patch(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    jdId: Optional[str] = None
    resumeId: Optional[str] = None
    statuses: Optional[Dict[str, str]] = None
    artifacts: Optional[Dict[str, object]] = None

class RunResultV2(BaseModel):
    pipeline: PipelineV2
    log: List[str]

_CACHE_GET = TTLCache(maxsize=1024, ttl=15)
_CACHE_LIST = TTLCache(maxsize=1, ttl=10)

V2_ORDER = [
    "intake","jd","profile","gaps","differentiators","draft","compliance","ats","benchmark","actions","export"
]

def _ensure_single_active_v2(statuses: Dict[str, str]) -> Dict[str, str]:
    out = dict(statuses)
    first_pending = next((k for k in V2_ORDER if out.get(k) != "complete"), None)
    for k in V2_ORDER:
        out[k] = "complete" if out.get(k) == "complete" else "pending"
    if first_pending:
        out[first_pending] = "active"
    return out

def _to_pydantic(row) -> PipelineV2:
    data = json.loads(row.statuses_json or "{}")
    statuses = data.get("statuses", data)  # support storing nested {statuses, artifacts}
    artifacts = data.get("artifacts")
    # Backfill missing keys with 'pending'
    full: Dict[str, str] = {k: statuses.get(k, "pending") for k in V2_ORDER}
    return PipelineV2(
        id=row.id,
        name=row.name,
        createdAt=row.created_at_ms,
        company=row.company,
        jdId=row.jd_id,
        resumeId=row.resume_id,
        statuses=V2Statuses(**full),
        artifacts=artifacts or {},
    )

def _migrate_legacy_if_needed(db, id: str) -> Optional[PipelineV2Record]:
    """If a legacy row exists (in pipelines table) for given id, copy it into pipelines_v2."""
    legacy = db.get(LegacyPipeline, id)
    if not legacy:
        return None
    data = json.loads(legacy.statuses_json or "{}")
    payload = data if ("statuses" in data or "artifacts" in data) else {"statuses": data, "artifacts": {}}
    row = PipelineV2Record(
        id=legacy.id,
        name=legacy.name,
        created_at_ms=legacy.created_at_ms,
        company=legacy.company,
        jd_id=legacy.jd_id,
        resume_id=legacy.resume_id,
        statuses_json=json.dumps(payload),
    )
    db.add(row)
    db.commit(); db.refresh(row)
    return row


async def _analyze_and_update(db, row: PipelineV2Record) -> None:
    data = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
    statuses: Dict[str, str] = data.get("statuses", {})
    artifacts: Dict[str, object] = data.get("artifacts", {})

    if not row.jd_id:
        # Nothing to analyze
        row.statuses_json = json.dumps({"statuses": statuses, "artifacts": artifacts}); db.add(row); db.commit(); db.refresh(row)
        return

    # Use enhanced extractor with comprehensive anti-bot capabilities
    try:
        logger.info(f"🚀 Starting enhanced JD extraction for pipeline {row.id}")
        
        # Use enhanced extractor with comprehensive anti-bot protection
        extraction_result = await enhanced_extractor.extract_with_antibot(
            row.jd_id, 
            pipeline_id=str(row.id)
        )
        
        if extraction_result.get("success"):
            extracted = extraction_result["data"]
            title = extracted.get("title") or row.name
            company = extracted.get("company") or row.company
            desc = extracted.get("description") or ""
            
            # Log extraction quality
            quality_score = extraction_result.get("quality_score", 0.0)
            method = extraction_result.get("extraction_method", "unknown")
            logger.info(f"✅ JD extraction successful for pipeline {row.id} - Method: {method}, Quality: {quality_score:.2f}")
            
            try:
                desc = normalize_jd_text(desc)
            except Exception:
                pass
            reqs = _extract_key_requirements(desc)
            matched, total, pct, details = _coverage(desc, reqs)
            artifacts["jd"] = {
                "url": row.jd_id,
                "title": title,
                "company": company,
                "description": desc,
                "extraction_metadata": {
                    "method": method,
                    "quality_score": quality_score,
                    "timestamp": extraction_result.get("timestamp"),
                    **extracted.get("extraction_metadata", {})
                },
                "key_requirements": reqs,
                "coverage": {"matched": matched, "total": total, "percent": round(pct, 2)},
                "matches": details,
            }
            statuses["jd"] = "complete" if (desc and reqs) else "pending"
            row.name = title or row.name
            row.company = company or row.company
        else:
            # Extraction failed, log error and set status
            error_msg = extraction_result.get("error", "Unknown extraction error")
            logger.error(f"❌ JD extraction failed for pipeline {row.id}: {error_msg}")
            
            artifacts["jd"] = {
                "url": row.jd_id,
                "error": error_msg,
                "extraction_metadata": {
                    "method": "failed",
                    "quality_score": 0.0,
                    "timestamp": extraction_result.get("timestamp")
                }
            }
            statuses["jd"] = "failed"
        
        # Always update the record
        row.statuses_json = json.dumps({"statuses": statuses, "artifacts": artifacts})
        db.add(row)
        db.commit()
        db.refresh(row)
        
    except Exception as e:
        # Last resort fallback - use basic fetch with anti-bot detection
        logger.warning(f"⚠️ Enhanced extraction threw exception for pipeline {row.id}, trying fallback: {e}")
        
        try:
            # Try IP rotation manager for fallback
            html, status, blocked_reason = await enhanced_extractor.ip_manager.fetch_with_rotation(row.jd_id)
            
            if blocked_reason:
                logger.error(f"🚫 Fallback fetch blocked for pipeline {row.id}: {blocked_reason}")
                statuses["jd"] = "blocked"
                artifacts["jd"] = {
                    "url": row.jd_id,
                    "error": f"All extraction methods blocked: {blocked_reason}",
                    "blocked_reason": blocked_reason
                }
            elif status >= 400:
                statuses["jd"] = "failed"
                artifacts["jd"] = {
                    "url": row.jd_id,
                    "error": f"HTTP {status} error",
                    "status_code": status
                }
            else:
                # Basic extraction as last resort
                extracted = SimpleJobExtractor().extract(row.jd_id, html)
                title = extracted.get("title") or row.name
                company = extracted.get("company") or row.company
                desc = extracted.get("description") or ""
                
                try:
                    desc = normalize_jd_text(desc)
                except Exception:
                    pass
                    
                reqs = _extract_key_requirements(desc)
                matched, total, pct, details = _coverage(desc, reqs)
                artifacts["jd"] = {
                    "url": row.jd_id,
                    "title": title,
                    "company": company,
                    "description": desc,
                    "extraction_metadata": {
                        "method": "fallback_basic",
                        "quality_score": 0.5,  # Default fallback score
                        "timestamp": time.time()
                    },
                    "key_requirements": reqs,
                    "coverage": {"matched": matched, "total": total, "percent": round(pct, 2)},
                    "matches": details,
                }
                statuses["jd"] = "complete" if (desc and reqs) else "pending"
                row.name = title or row.name
                row.company = company or row.company
                
                logger.info(f"✅ Fallback extraction successful for pipeline {row.id}")
            
        except Exception as fallback_error:
            logger.error(f"❌ Complete extraction failure for pipeline {row.id}: {fallback_error}")
            statuses["jd"] = "failed"
            artifacts["jd"] = {
                "url": row.jd_id,
                "error": f"All extraction methods failed: {str(e)} | Fallback: {str(fallback_error)}",
                "extraction_metadata": {
                    "method": "failed",
                    "quality_score": 0.0,
                    "timestamp": time.time()
                }
            }
        
        # Always update the record
        row.statuses_json = json.dumps({"statuses": statuses, "artifacts": artifacts})
        db.add(row)
        db.commit()
        db.refresh(row)

@router.get("", response_model=List[PipelineV2])
async def list_pipelines_v2() -> List[PipelineV2]:
    if _CACHE_LIST:
        try:
            return _CACHE_LIST["list"]
        except KeyError:
            pass
    with SessionLocal() as db:
        rows_v2 = db.execute(select(PipelineV2Record).order_by(PipelineV2Record.created_at_ms.desc())).scalars().all()
        # Include unmigrated legacy rows that follow v2 id pattern
        v2_ids = {r.id for r in rows_v2}
        rows_legacy = db.execute(select(LegacyPipeline).where(LegacyPipeline.id.like("pl2_%")).order_by(LegacyPipeline.created_at_ms.desc())).scalars().all()
        rows_legacy = [r for r in rows_legacy if r.id not in v2_ids]
    items = [_to_pydantic(r) for r in rows_v2] + [_to_pydantic(r) for r in rows_legacy]
    _CACHE_LIST["list"] = items
    return items

@router.post("", response_model=PipelineV2, status_code=201)
async def create_pipeline_v2(body: PipelineV2Create, background: BackgroundTasks) -> PipelineV2:
    pid = f"pl2_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    created = int(time.time() * 1000)
    statuses = V2Statuses(**{k: "pending" for k in V2_ORDER})
    payload = {"statuses": statuses.model_dump(), "artifacts": {}}
    with SessionLocal() as db:
        row = PipelineV2Record(
            id=pid,
            name=body.name,
            created_at_ms=created,
            company=body.company,
            jd_id=body.jdId,
            resume_id=body.resumeId,
            statuses_json=json.dumps(payload),
        )
        db.add(row)
        db.commit(); db.refresh(row)
        # Mark intake complete immediately
        data = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
        st = data.get("statuses", {})
        art = data.get("artifacts", {})
        st.setdefault("intake", "complete")
        
        # Check if JD is manual text or URL
        if body.jdId:
            # Check if it's manual text (starts with "manual:")
            if body.jdId.startswith("manual:"):
                # Extract the manual text
                manual_text = body.jdId[7:]  # Remove "manual:" prefix
                logger.info(f"📝 Using manual JD text for pipeline {pid}")
                
                # Directly store the manual JD as complete
                try:
                    desc = normalize_jd_text(manual_text)
                except Exception:
                    desc = manual_text
                    
                reqs = _extract_key_requirements(desc)
                matched, total, pct, details = _coverage(desc, reqs)
                
                art["jd"] = {
                    "url": "manual",
                    "title": body.name,
                    "company": body.company,
                    "description": desc,
                    "extraction_metadata": {
                        "method": "manual",
                        "quality_score": 1.0,
                        "timestamp": time.time(),
                        "source": "user_input"
                    },
                    "key_requirements": reqs,
                    "coverage": {"matched": matched, "total": total, "percent": round(pct, 2)},
                    "matches": details,
                }
                st["jd"] = "complete"
            else:
                # It's a URL - enqueue background analysis
                try:
                    job_id = enqueue_jd_analysis(pid, body.jdId)
                    art["jd_job_id"] = job_id
                    # set JD status to pending (worker will flip to complete)
                    st.setdefault("jd", "pending")
                except Exception:
                    # Best-effort; if queue fails, leave as pending
                    st.setdefault("jd", "pending")

        # If a resume is directly provided as manual text via resumeId prefixed with "manual:", ingest it
        if body.resumeId:
            if body.resumeId.startswith("manual:"):
                resume_text = body.resumeId[7:]
                logger.info(f"📥 Ingesting manual resume text for pipeline {pid}")
                try:
                    # Use pipeline id as candidate id to group chunks
                    client = ingest_module.chroma_client.ChromaClient()
                    collection = client.get_collection()
                    count = ingest_module.ingest_candidate(pid, resume_text, metadata={"source": "pipeline_manual_resume"}, collection=collection)
                    artifacts["resume"] = {"source": "manual", "chunks_indexed": count}
                    # mark profile step as complete if we have chunks
                    st.setdefault("profile", "pending")
                    if count > 0:
                        st["profile"] = "complete"
                except Exception as e:
                    logger.warning(f"Failed to ingest manual resume for pipeline {pid}: {e}")
                    artifacts.setdefault("resume", {})["error"] = str(e)
        
        # Optionally simulate profile ready once JD completes; worker will set profile when saving artifacts
        row.statuses_json = json.dumps({"statuses": st, "artifacts": art})
        db.add(row); db.commit(); db.refresh(row)

    pipe = PipelineV2(id=pid, name=body.name, createdAt=created, company=body.company, jdId=body.jdId, resumeId=body.resumeId, statuses=statuses, artifacts={})
    _CACHE_GET.clear(); _CACHE_LIST.clear()
    return pipe


@router.get("/{id}/jd/stream", tags=["pipelines-v2"])
async def stream_jd_ready(id: str, request: Request):
    """Server-Sent Events stream that completes when artifacts.jd exists for the pipeline.
    Sends periodic keep-alives to keep connection open.
    
    Note: This endpoint uses custom logging to reduce log spam.
    """
    # Use a flag to track if we've logged initial connection
    _logged_connection = False
    
    async def event_gen():
        start = int(time.time())
        # Immediate check
        try:
            with SessionLocal() as db:
                row = db.get(PipelineV2Record, id)
                if not row:
                    yield "event: error\n" + f"data: {json.dumps({'error': 'not_found'})}\n\n"
                    return
                data = json.loads(row.statuses_json or "{}")
                artifacts = data.get("artifacts", {})
                if artifacts.get("jd"):
                    yield "event: ready\n" + f"data: {json.dumps({'ready': True})}\n\n"
                    return
                # If job id exists, emit initial status
                job_id = artifacts.get("jd_job_id")
                if job_id:
                    job = get_job(job_id) or {}
                    # If job already failed, emit failed and end
                    if job.get("status") == "failed":
                        payload = {
                            'error': job.get('error','unknown')
                        }
                        if isinstance(job.get('data'), dict):
                            payload['details'] = {k: job['data'].get(k) for k in ['stage','strategy','http_status','blocked_marker','url','progress'] if k in job['data']}
                        if isinstance(job.get('artifacts'), dict) and job['artifacts'].get('html_snippet'):
                            payload['htmlSnippet'] = job['artifacts']['html_snippet']
                        yield "event: failed\n" + f"data: {json.dumps(payload)}\n\n"
                        return
                    msg, eta = _estimate_status(job)
                    data = job.get("data") or {}
                    payload = {
                        'status': job.get('status', 'queued'),
                        'etaSeconds': eta,
                        'message': msg,
                    }
                    if isinstance(data, dict):
                        if 'stage' in data:
                            payload['stage'] = data.get('stage')
                        if 'progress' in data:
                            payload['progress'] = data.get('progress')
                    yield "event: status\n" + f"data: {json.dumps(payload)}\n\n"
        except Exception:
            pass
        # Poll DB server-side until ready or client disconnects
        while True:
            if await request.is_disconnected():
                break
            try:
                with SessionLocal() as db:
                    row = db.get(PipelineV2Record, id)
                    if not row:
                        yield "event: error\n" + f"data: {json.dumps({'error': 'not_found'})}\n\n"
                        return
                    data = json.loads(row.statuses_json or "{}")
                    artifacts = data.get("artifacts", {})
                    if artifacts.get("jd"):
                        yield "event: ready\n" + f"data: {json.dumps({'ready': True})}\n\n"
                        return
                    # Stream status updates while waiting
                    job_id = artifacts.get("jd_job_id")
                    if job_id:
                        job = get_job(job_id) or {}
                        if job.get("status") == "failed":
                            payload = {
                                'error': job.get('error','unknown')
                            }
                            if isinstance(job.get('data'), dict):
                                payload['details'] = {k: job['data'].get(k) for k in ['stage','strategy','http_status','blocked_marker','url','progress'] if k in job['data']}
                            if isinstance(job.get('artifacts'), dict) and job['artifacts'].get('html_snippet'):
                                payload['htmlSnippet'] = job['artifacts']['html_snippet']
                            yield "event: failed\n" + f"data: {json.dumps(payload)}\n\n"
                            return
                        msg, eta = _estimate_status(job)
                        data = job.get("data") or {}
                        payload = {
                            'status': job.get('status', 'queued'),
                            'etaSeconds': eta,
                            'message': msg,
                        }
                        if isinstance(data, dict):
                            if 'stage' in data:
                                payload['stage'] = data.get('stage')
                            if 'progress' in data:
                                payload['progress'] = data.get('progress')
                        yield "event: status\n" + f"data: {json.dumps(payload)}\n\n"
            except Exception:
                # swallow and continue
                pass
            # timeout guard (90s)
            if int(time.time()) - start > 90:
                yield "event: timeout\n" + f"data: {json.dumps({'timeout': True})}\n\n"
                return
            # heartbeat every 1s
            yield "event: keepalive\n" + "data: {}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def _estimate_status(job: Dict[str, object]) -> tuple[str, int]:
    """Return (message, etaSeconds) for a JD job based on its status and queue length.
    This is a heuristic to give the user feedback during processing.
    """
    try:
        status = str(job.get("status", "queued"))
        now = int(time.time())
        if status == "queued":
            # Estimate wait based on queue length
            r = get_client()
            qlen = int(r.llen(JD_QUEUE_KEY) or 0)
            eta = min(45, 5 + qlen * 3)
            msg = f"Queued ({qlen} ahead). ~{eta}s remaining"
            return msg, eta
        if status == "running":
            # Running includes fetch + extract + normalize; aim 10–30s total
            started = int(job.get("updated_at") or now)
            elapsed = max(0, now - started)
            total = 20
            eta = max(5, total - elapsed)
            msg = f"Processing JD (fetching and extracting)… ~{eta}s"
            return msg, eta
        if status == "completed":
            return "Finalizing…", 1
        if status == "failed":
            return f"Failed: {job.get('error', 'unknown error')}", 0
    except Exception:
        pass
    return "Preparing job…", 10


@router.post("/{id}/jd/retry", response_model=PipelineV2)
async def retry_jd_analysis(id: str) -> PipelineV2:
    """Re-enqueue JD analysis with enhanced anti-bot capabilities for this pipeline."""
    with SessionLocal() as db:
        row = db.get(PipelineV2Record, id)
        if not row:
            row = _migrate_legacy_if_needed(db, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if not row.jd_id:
            raise HTTPException(status_code=400, detail="Pipeline has no jdId (job URL)")

        data = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
        statuses: Dict[str, str] = data.get("statuses", {})
        artifacts: Dict[str, object] = data.get("artifacts", {})
        
        logger.info(f"🔄 Retrying JD analysis with enhanced anti-bot for pipeline {id}")
        
        try:
            # First, try immediate enhanced extraction
            extraction_result = await enhanced_extractor.extract_with_antibot(
                row.jd_id, 
                pipeline_id=id
            )
            
            if extraction_result.get("success"):
                # Direct success - update immediately
                extracted = extraction_result["data"]
                title = extracted.get("title") or row.name
                company = extracted.get("company") or row.company
                desc = extracted.get("description") or ""
                
                try:
                    desc = normalize_jd_text(desc)
                except Exception:
                    pass
                    
                reqs = _extract_key_requirements(desc)
                matched, total, pct, details = _coverage(desc, reqs)
                
                artifacts["jd"] = {
                    "url": row.jd_id,
                    "title": title,
                    "company": company,
                    "description": desc,
                    "extraction_metadata": {
                        "method": extraction_result.get("extraction_method", "enhanced"),
                        "quality_score": extraction_result.get("quality_score", 0.0),
                        "timestamp": extraction_result.get("timestamp"),
                        "retry_attempt": True,
                        **extracted.get("extraction_metadata", {})
                    },
                    "key_requirements": reqs,
                    "coverage": {"matched": matched, "total": total, "percent": round(pct, 2)},
                    "matches": details,
                }
                statuses["jd"] = "complete"
                row.name = title or row.name
                row.company = company or row.company
                
                # Clear any error states
                artifacts.pop("jd_error", None)
                artifacts.pop("blocked_reason", None)
                
                logger.info(f"✅ Enhanced retry successful for pipeline {id} - Method: {extraction_result.get('extraction_method')}, Quality: {extraction_result.get('quality_score', 0.0):.2f}")
                
            else:
                # Enhanced extraction failed, fall back to worker queue but with anti-bot metadata
                logger.warning(f"⚠️ Enhanced retry failed for pipeline {id}, falling back to worker queue: {extraction_result.get('error')}")
                
                job_id = enqueue_jd_analysis(id, row.jd_id)
                artifacts["jd_job_id"] = job_id
                artifacts["retry_metadata"] = {
                    "enhanced_extraction_failed": True,
                    "enhanced_error": extraction_result.get("error"),
                    "fallback_to_worker": True,
                    "timestamp": time.time()
                }
                statuses["jd"] = "pending"
                
            row.statuses_json = json.dumps({"statuses": statuses, "artifacts": artifacts})
            db.add(row)
            db.commit()
            db.refresh(row)
            
        except Exception as e:
            logger.error(f"❌ Enhanced retry completely failed for pipeline {id}: {e}")
            raise HTTPException(status_code=500, detail=f"Enhanced retry failed: {e}")

    _CACHE_GET.pop(id, None); _CACHE_LIST.clear()
    return _to_pydantic(row)

@router.get("/{id}", response_model=PipelineV2)
async def get_pipeline_v2(id: str) -> PipelineV2:
    try:
        return _CACHE_GET[id]
    except KeyError:
        pass
    with SessionLocal() as db:
        row = db.get(PipelineV2Record, id)
        if not row:
            row = _migrate_legacy_if_needed(db, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
    item = _to_pydantic(row)
    _CACHE_GET[id] = item
    return item

@router.patch("/{id}", response_model=PipelineV2)
async def patch_pipeline_v2(id: str, body: PipelineV2Patch) -> PipelineV2:
    with SessionLocal() as db:
        row = db.get(PipelineV2Record, id)
        if not row:
            row = _migrate_legacy_if_needed(db, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        data = json.loads(row.statuses_json or "{}")
        statuses = data.get("statuses", {})
        artifacts = data.get("artifacts", {})
        if body.name is not None:
            row.name = body.name
        if body.company is not None:
            row.company = body.company
        if body.jdId is not None:
            row.jd_id = body.jdId
        if body.resumeId is not None:
            row.resume_id = body.resumeId
        if body.statuses is not None and isinstance(body.statuses, dict):
            statuses = {**statuses, **body.statuses}
        if body.artifacts is not None and isinstance(body.artifacts, dict):
            artifacts = {**artifacts, **body.artifacts}
        row.statuses_json = json.dumps({"statuses": statuses, "artifacts": artifacts})
        db.add(row)
        db.commit(); db.refresh(row)
    _CACHE_GET.pop(id, None); _CACHE_LIST.clear()
    return _to_pydantic(row)

@router.post("/{id}/run", response_model=RunResultV2)
async def run_pipeline_v2(id: str) -> RunResultV2:
    log: List[str] = []
    with SessionLocal() as db:
        row = db.get(PipelineV2Record, id)
        if not row:
            row = _migrate_legacy_if_needed(db, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        data = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
        statuses: Dict[str, str] = data.get("statuses", {})
        artifacts: Dict[str, object] = data.get("artifacts", {})
        # Initialize
        for k in V2_ORDER:
            statuses.setdefault(k, "pending")
        statuses = _ensure_single_active_v2(statuses)
        row.statuses_json = json.dumps({"statuses": statuses, "artifacts": artifacts}); db.add(row); db.commit(); db.refresh(row)

        # Simulate step execution in order
        # Real agentic execution: run meaningful work per step and capture artifacts and scores
        chroma_collection = ChromaClient().get_collection()
        for step in V2_ORDER:
                statuses[step] = "active"
                row.statuses_json = json.dumps({"statuses": statuses, "artifacts": artifacts}); db.add(row); db.commit(); db.refresh(row)
                try:
                    if step == "intake":
                        # record intake timestamp
                        artifacts.setdefault("intake", {})
                        artifacts["intake"]["ranAt"] = time.time()
                        log.append("intake: recorded")

                    elif step == "jd":
                        if row.jd_id:
                            extraction_result = await enhanced_extractor.extract_with_antibot(row.jd_id, pipeline_id=row.id)
                            if extraction_result.get("success"):
                                extracted = extraction_result["data"]
                                desc = extracted.get("description", "")
                                try:
                                    desc = normalize_jd_text(desc)
                                except Exception:
                                    pass
                                reqs = _extract_key_requirements(desc)
                                matched, total, pct, details = _coverage(desc, reqs)
                                artifacts["jd"] = {
                                    "url": row.jd_id,
                                    "title": extracted.get("title") or row.name,
                                    "company": extracted.get("company") or row.company,
                                    "description": desc,
                                    "extraction_metadata": extraction_result.get("extraction_metadata", {}),
                                    "quality_score": extraction_result.get("quality_score", 0.0),
                                    "key_requirements": reqs,
                                    "coverage": {"matched": matched, "total": total, "percent": round(pct, 2)},
                                    "matches": details,
                                }
                                log.append(f"jd: extracted (quality={artifacts['jd']['quality_score']:.2f})")
                            else:
                                artifacts["jd"] = {"error": extraction_result.get("error")}
                                log.append("jd: extraction_failed")

                    elif step == "profile":
                        # obtain resume text (from resume_id or stored artifact)
                        resume_text = None
                        if row.resume_id:
                            try:
                                resume_text = fetch_text(row.resume_id)
                            except Exception:
                                resume_text = None
                        if not resume_text and artifacts.get("resume"):
                            resume_text = artifacts.get("resume", {}).get("text")
                        if resume_text:
                            parsed = extract_profile_from_text(resume_text)
                            normalized = normalize_skills(parsed.get("skills", []) or [])
                            # coerce normalized to dict if needed
                            if normalized is None:
                                normalized = {}
                            elif isinstance(normalized, list):
                                normalized = {"skills": normalized}
                            artifacts["profile"] = {"parsed": parsed, "normalized_skills": normalized}
                            log.append("profile: parsed and normalized")
                        else:
                            artifacts["profile"] = {"error": "no_resume"}
                            log.append("profile: no_resume")

                    elif step in ("gaps", "differentiators", "analysis"):
                        # compute coverage/gap analysis if we have JD and profile
                        jd_desc = (artifacts.get("jd") or {}).get("description", "")
                        parsed = (artifacts.get("profile") or {}).get("parsed") or {}
                        reqs = _extract_key_requirements(jd_desc)
                        matched, total, pct, details = _coverage(" ".join([parsed.get("summary",""), jd_desc]), reqs)
                        artifacts.setdefault("analysis", {})
                        artifacts["analysis"]["coverage"] = {"matched": matched, "total": total, "percent": round(pct,2)}
                        artifacts["analysis"]["details"] = details
                        log.append(f"{step}: analysis_done (coverage={pct:.1f}%)")

                    elif step == "ats":
                        # score profile against JD
                        parsed = (artifacts.get("profile") or {}).get("parsed") or {}
                        jd_desc = (artifacts.get("jd") or {}).get("description", "")
                        score = score_profile(parsed, {"description": jd_desc, "top_keywords": []})
                        artifacts["ats"] = score
                        log.append(f"ats: scored (aggregate={score.get('aggregate')})")

                    elif step == "actions":
                        # generate tailored resume and optimization
                        parsed = (artifacts.get("profile") or {}).get("parsed") or {}
                        jd_desc = (artifacts.get("jd") or {}).get("description", "")
                        try:
                            generated = generate_resume(parsed, query=jd_desc, top_k=5, llm="deepseek/DeepSeek-R1-0528", collection=chroma_collection)
                        except Exception as e:
                            generated = str(e)
                        # optimize bullets
                        exp_list = parsed.get("experience") or [generated]
                        bullets = optimize_experience_bullets(exp_list)
                        artifacts.setdefault("generated", {})
                        artifacts["generated"]["resume_text"] = generated
                        artifacts["generated"]["optimized_bullets"] = bullets
                        log.append("actions: generated and optimized")

                    elif step == "export":
                        parsed = (artifacts.get("profile") or {}).get("parsed") or {}
                        bullets = (artifacts.get("generated") or {}).get("optimized_bullets") or []
                        txt = format_txt(parsed, bullets)
                        docx_bytes = format_docx(parsed, bullets)
                        artifacts.setdefault("export", {})
                        artifacts["export"]["txt"] = txt
                        artifacts["export"]["docx_len"] = len(docx_bytes)
                        log.append(f"export: prepared (docx_len={len(docx_bytes)})")

                    # mark complete for this step
                    statuses[step] = "complete"
                except Exception as e:
                    logger.exception(f"Error running step {step} for pipeline {id}: {e}")
                    statuses[step] = "failed"
                    artifacts.setdefault("errors", []).append({"step": step, "error": str(e)})
                    log.append(f"{step}: failed - {str(e)}")

                # persist changes and ensure next active
                statuses = _ensure_single_active_v2(statuses)
                row.statuses_json = json.dumps({"statuses": statuses, "artifacts": artifacts}); db.add(row); db.commit(); db.refresh(row)

    _CACHE_GET.pop(id, None); _CACHE_LIST.clear()
    return RunResultV2(pipeline=_to_pydantic(row), log=log)


@router.post("/{id}/upload")
async def upload_pipeline_artifacts(id: str, jd_url: Optional[str] = None, jd_file: UploadFile | None = File(None), resume_file: UploadFile | None = File(None)):
    """Upload JD (URL or file) and resume file to attach to a pipeline. Extracts text and stores in artifacts.

    jd_url takes precedence over jd_file. If jd_file is provided, its text will be extracted using fetcher.extract_text_from_bytes.
    """
    with SessionLocal() as db:
        row = db.get(PipelineV2Record, id)
        if not row:
            row = _migrate_legacy_if_needed(db, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        data = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
        artifacts: Dict[str, object] = data.get("artifacts", {})

        # JD URL preference
        if jd_url:
            row.jd_id = jd_url
            # attempt quick fetch and store description if small
            try:
                desc = await enhanced_extractor.extract_with_antibot(jd_url, pipeline_id=id)
                if desc.get("success"):
                    artifacts.setdefault("jd", {})
                    artifacts["jd"].update({
                        "url": jd_url,
                        "title": desc["data"].get("title"),
                        "company": desc["data"].get("company"),
                        "description": desc["data"].get("description"),
                        "extraction_metadata": desc.get("extraction_metadata", {}),
                        "quality_score": desc.get("quality_score", 0.0),
                    })
            except Exception:
                # ignore extraction errors; jdId stored for later analysis
                pass

        # File uploads
        from app.utils.fetcher import extract_text_from_bytes
        from app import storage
        from app.tasks import parse_resume_task
        from app.celery_app import celery_app
        from app.utils.queue import get_job

        if jd_file is not None:
            data_bytes = await jd_file.read()
            # Persist original JD file to MinIO for durability
            try:
                object_name = f"pipelines/{id}/jd/{uuid.uuid4().hex}_{jd_file.filename}"
                minio_uri = storage.upload_bytes(data_bytes, object_name, content_type=jd_file.content_type or "application/octet-stream")
                artifacts.setdefault("jd", {})
                artifacts["jd"].update({"minio_uri": minio_uri, "filename": jd_file.filename})
            except Exception as e:
                # best-effort: continue with text extraction even if upload fails
                artifacts.setdefault("jd", {})
                artifacts["jd"].setdefault("upload_error", str(e))
            # also extract text for immediate UX
            try:
                text = extract_text_from_bytes(data_bytes, filename=jd_file.filename or None, content_type=jd_file.content_type or None)
                artifacts["jd"].update({"description": text, "title": jd_file.filename})
            except Exception:
                pass
            await jd_file.close()

        if resume_file is not None:
            data_bytes = await resume_file.read()
            artifacts.setdefault("resume", {})
            artifacts["resume"].update({"filename": resume_file.filename})
            # Persist resume bytes to MinIO and enqueue background parse task
            try:
                object_name = f"pipelines/{id}/resume/{uuid.uuid4().hex}_{resume_file.filename}"
                minio_uri = storage.upload_bytes(data_bytes, object_name, content_type=resume_file.content_type or "application/octet-stream")
                artifacts["resume"]["minio_uri"] = minio_uri

                # Parse minio://bucket/object into bucket and object_key
                try:
                    assert minio_uri.startswith("minio://")
                    _, rest = minio_uri.split("minio://", 1)
                    bucket, object_key = rest.split("/", 1)
                except Exception:
                    bucket = storage.MINIO_BUCKET if hasattr(storage, "MINIO_BUCKET") else "talentflow"
                    object_key = object_name

                # enqueue parse task (candidate id = pipeline id)
                try:
                    async_result = parse_resume_task.delay(id, bucket, object_key)
                    artifacts["resume"]["parse_job_id"] = async_result.id
                    artifacts["resume"]["parse_job_status"] = "queued"
                except Exception as e:
                    artifacts["resume"]["parse_enqueue_error"] = str(e)

                # also extract text for immediate UX (best-effort)
                try:
                    text = extract_text_from_bytes(data_bytes, filename=resume_file.filename or None, content_type=resume_file.content_type or None)
                    artifacts["resume"]["text"] = text
                except Exception:
                    pass

            except Exception as e:
                artifacts["resume"]["upload_error"] = str(e)
            await resume_file.close()

        row.statuses_json = json.dumps({"statuses": data.get("statuses", {}), "artifacts": artifacts})
        db.add(row); db.commit(); db.refresh(row)
    _CACHE_GET.pop(id, None); _CACHE_LIST.clear()
    return _to_pydantic(row)


@router.get("/{id}/upload-status")
async def get_upload_status(id: str):
    """Return upload & parse job status for the pipeline intake (JD and resume)."""
    with SessionLocal() as db:
        row = db.get(PipelineV2Record, id)
        if not row:
            row = _migrate_legacy_if_needed(db, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        data = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
        artifacts: Dict[str, object] = data.get("artifacts", {})

    result: Dict[str, object] = {"artifacts": artifacts, "jobs": {}}

    # JD queue job
    jd_job_id = (artifacts.get("jd") or {}).get("job_id") or (artifacts.get("jd") or {}).get("jd_job_id")
    if jd_job_id:
        try:
            job = get_job(jd_job_id)
            result["jobs"]["jd"] = job or {"id": jd_job_id}
        except Exception:
            result["jobs"]["jd"] = {"id": jd_job_id}

    # Resume parse job (Celery)
    resume_parse_id = (artifacts.get("resume") or {}).get("parse_job_id")
    if resume_parse_id:
        try:
            ar = celery_app.AsyncResult(resume_parse_id)
            result["jobs"]["resume_parse"] = {"id": resume_parse_id, "state": getattr(ar, "state", None) or getattr(ar, "status", None)}
        except Exception:
            result["jobs"]["resume_parse"] = {"id": resume_parse_id}

    return result

@router.delete("/{id}")
async def delete_pipeline_v2(id: str):
    with SessionLocal() as db:
        row = db.get(PipelineV2Record, id)
        if row:
            db.delete(row)
            db.commit()
        else:
            legacy = db.get(LegacyPipeline, id)
            if not legacy:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            db.delete(legacy)
            db.commit()
    _CACHE_GET.pop(id, None); _CACHE_LIST.clear()
    return {"ok": True}


# ---- JD analysis helpers and route ----

def _extract_key_requirements(desc: str) -> List[str]:
    """Heuristic extraction of key requirements from a JD description.
    - Prefer bullet-like lines
    - Fallback to sentences mentioning years/skills/tools
    """
    text = desc or ""
    lines = [l.strip() for l in text.splitlines()]
    bullets = []
    for l in lines:
        if re.match(r"^[-*•\u2022\u25CF]\s+", l) or re.match(r"^\d+\.", l):
            bullets.append(re.sub(r"^([-*•\u2022\u25CF]|\d+\.)\s+", "", l).strip())
    reqs = [b for b in bullets if len(b) > 0]
    if len(reqs) >= 3:
        return reqs[:25]
    # Fallback: pick sentences with strong signals
    sentences = re.split(r"(?<=[.!?])\s+", text)
    strong = []
    patterns = [
        r"\b\d+\+?\s+(years|yrs)\b",
        r"\b(experience|proficien\w*|expert\w*|knowledge)\b",
        r"\b(react|vue|angular|svelte|node\.?js|express|django|flask|fastapi|spring)\b",
        r"\b(aws|azure|gcp|docker|kubernetes|jenkins|git|postgresql|mysql|mongodb)\b",
        r"\b(python|javascript|typescript|java|go|rust|php|ruby|swift|kotlin|c\+\+|c#)\b",
    ]
    for s in sentences:
        low = s.lower()
        if any(re.search(p, low) for p in patterns):
            strong.append(s.strip())
    if strong:
        return strong[:20]
    # Last resort: top non-empty lines
    return [l for l in lines if l][:10]


def _coverage(desc: str, reqs: List[str]) -> Tuple[int, int, float, List[Dict[str, object]]]:
    """Compute simple coverage: requirement considered matched if half of its tokens appear in description."""
    base = (desc or "").lower()
    base_tokens = set(re.findall(r"[a-z0-9+#.]+", base))
    results = []
    matched = 0
    for r in reqs:
        tokens = [t for t in re.findall(r"[a-z0-9+#.]+", r.lower()) if len(t) > 1]
        if not tokens:
            results.append({"requirement": r, "matched": False, "score": 0.0})
            continue
        overlap = sum(1 for t in tokens if t in base_tokens)
        score = overlap / max(len(tokens), 1)
        ok = score >= 0.5 or (overlap >= 2 and len(tokens) <= 4)
        matched += 1 if ok else 0
        results.append({"requirement": r, "matched": ok, "score": round(score, 3)})
    total = len(reqs)
    pct = (matched / total * 100.0) if total else 0.0
    return matched, total, pct, results


@router.post("/{id}/analyze-jd", response_model=PipelineV2)
async def analyze_jd(id: str) -> PipelineV2:
    """Fetch JD for the pipeline (using jdId URL), extract title/company/description,
    infer key requirements, compute coverage, and persist to artifacts.jd.
    """
    with SessionLocal() as db:
        row = db.get(PipelineV2Record, id)
        if not row:
            row = _migrate_legacy_if_needed(db, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if not row.jd_id:
            raise HTTPException(status_code=400, detail="Pipeline has no jdId (job URL)")

        # Load existing artifacts
        data = json.loads(row.statuses_json or "{}") or {"statuses": {}, "artifacts": {}}
        statuses: Dict[str, str] = data.get("statuses", {})
        artifacts: Dict[str, object] = data.get("artifacts", {})

        # Enhanced fetch and extract with comprehensive anti-bot protection
        logger.info(f"🚀 Starting enhanced JD analysis for pipeline {id}")
        
        extraction_result = await enhanced_extractor.extract_with_antibot(
            row.jd_id,
            pipeline_id=id
        )
        
        if extraction_result.get("success"):
            extracted = extraction_result["data"]
            title = extracted.get("title") or row.name
            company = extracted.get("company") or row.company
            desc = extracted.get("description") or ""
            
            # Log extraction success
            quality_score = extraction_result.get("quality_score", 0.0)
            method = extraction_result.get("extraction_method", "unknown")
            logger.info(f"✅ Enhanced JD analysis successful for pipeline {id} - Method: {method}, Quality: {quality_score:.2f}")
            
            try:
                desc = normalize_jd_text(desc)
            except Exception:
                pass

            reqs = _extract_key_requirements(desc)
            matched, total, pct, details = _coverage(desc, reqs)
            artifacts["jd"] = {
                "url": row.jd_id,
                "title": title,
                "company": company,
                "description": desc,
                "extraction_metadata": {
                    "method": method,
                    "quality_score": quality_score,
                    "timestamp": extraction_result.get("timestamp"),
                    **extracted.get("extraction_metadata", {})
                },
                "key_requirements": reqs,
                "coverage": {"matched": matched, "total": total, "percent": round(pct, 2)},
                "matches": details,
            }
        else:
            # Enhanced extraction failed, throw appropriate error
            error_msg = extraction_result.get("error", "Enhanced extraction failed")
            logger.error(f"❌ Enhanced JD analysis failed for pipeline {id}: {error_msg}")
            
            # Try to determine specific error type
            if "blocked" in error_msg.lower() or "captcha" in error_msg.lower():
                raise HTTPException(status_code=403, detail=f"JD extraction blocked by anti-bot measures: {error_msg}")
            elif "timeout" in error_msg.lower():
                raise HTTPException(status_code=504, detail=f"JD extraction timed out: {error_msg}")
            else:
                raise HTTPException(status_code=502, detail=f"Failed to extract JD: {error_msg}")

        # Mark JD step complete if we have content
        statuses.setdefault("jd", "pending")
        if desc and reqs:
            statuses["jd"] = "complete"

        row.statuses_json = json.dumps({"statuses": statuses, "artifacts": artifacts})
        db.add(row)
        db.commit(); db.refresh(row)

    _CACHE_GET.pop(id, None); _CACHE_LIST.clear()
    return _to_pydantic(row)


@router.get("/stats/extraction")
async def get_extraction_stats() -> Dict[str, Any]:
    """Get comprehensive extraction statistics and anti-bot performance metrics."""
    try:
        # Get extraction stats from enhanced extractor
        extraction_stats = enhanced_extractor.get_extraction_stats()
        
        # Get IP rotation manager stats
        ip_stats = enhanced_extractor.ip_manager.get_rotation_stats()
        
        # Get recent pipeline success rates from database
        with SessionLocal() as db:
            # Get last 100 pipelines with JD analysis
            recent_pipelines = db.execute(
                select(PipelineV2Record)
                .where(PipelineV2Record.jd_id.isnot(None))
                .order_by(PipelineV2Record.created_at_ms.desc())
                .limit(100)
            ).scalars().all()
            
            pipeline_stats = {
                "total_pipelines_analyzed": len(recent_pipelines),
                "success_by_method": {},
                "quality_scores": [],
                "blocked_pipelines": 0,
                "failed_pipelines": 0,
                "extraction_methods": {}
            }
            
            for pipeline in recent_pipelines:
                try:
                    data = json.loads(pipeline.statuses_json or "{}")
                    artifacts = data.get("artifacts", {})
                    jd_data = artifacts.get("jd", {})
                    
                    if jd_data:
                        # Count by status
                        jd_status = data.get("statuses", {}).get("jd", "unknown")
                        
                        if jd_status == "complete":
                            # Extract method and quality information
                            metadata = jd_data.get("extraction_metadata", {})
                            method = metadata.get("method", "unknown")
                            quality_score = metadata.get("quality_score", 0.0)
                            
                            # Count by method
                            pipeline_stats["extraction_methods"][method] = pipeline_stats["extraction_methods"].get(method, 0) + 1
                            
                            # Track quality scores
                            if quality_score > 0:
                                pipeline_stats["quality_scores"].append(quality_score)
                                
                        elif jd_status == "blocked" or jd_data.get("blocked_reason"):
                            pipeline_stats["blocked_pipelines"] += 1
                        elif jd_status == "failed":
                            pipeline_stats["failed_pipelines"] += 1
                            
                except Exception as e:
                    logger.warning(f"Failed to parse pipeline stats for {pipeline.id}: {e}")
                    continue
            
            # Calculate averages
            if pipeline_stats["quality_scores"]:
                pipeline_stats["average_quality_score"] = sum(pipeline_stats["quality_scores"]) / len(pipeline_stats["quality_scores"])
                pipeline_stats["min_quality_score"] = min(pipeline_stats["quality_scores"])
                pipeline_stats["max_quality_score"] = max(pipeline_stats["quality_scores"])
            else:
                pipeline_stats["average_quality_score"] = 0.0
                pipeline_stats["min_quality_score"] = 0.0
                pipeline_stats["max_quality_score"] = 0.0
            
            # Calculate success rate
            successful = len(pipeline_stats["quality_scores"])
            total = pipeline_stats["total_pipelines_analyzed"]
            pipeline_stats["pipeline_success_rate"] = successful / total if total > 0 else 0.0
        
        # Combine all stats
        comprehensive_stats = {
            "timestamp": time.time(),
            "extraction_engine": extraction_stats,
            "ip_rotation": ip_stats,
            "pipeline_performance": pipeline_stats,
            "anti_bot_summary": {
                "total_attempts": extraction_stats.get("total_attempts", 0),
                "success_rate": extraction_stats.get("success_rate", 0.0),
                "block_rate": extraction_stats.get("block_rate", 0.0),
                "browser_automation_usage": extraction_stats.get("browser_automation_used", 0),
                "fallback_usage": extraction_stats.get("fallback_used", 0),
                "average_pipeline_quality": pipeline_stats.get("average_quality_score", 0.0)
            }
        }
        
        logger.info(f"📊 Extraction stats requested - Success rate: {extraction_stats.get('success_rate', 0.0):.2%}, Block rate: {extraction_stats.get('block_rate', 0.0):.2%}")
        
        return comprehensive_stats
        
    except Exception as e:
        logger.error(f"❌ Failed to generate extraction stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get extraction stats: {e}")


@router.post("/debug/test-extraction")
async def debug_test_extraction(url: str) -> Dict[str, Any]:
    """Debug endpoint to test extraction capabilities on a specific URL."""
    try:
        logger.info(f"🧪 Debug extraction test for: {url}")
        
        # Test with enhanced extractor
        extraction_result = await enhanced_extractor.extract_with_antibot(url, pipeline_id="debug")
        
        # Get additional debug info
        debug_info = {
            "url": url,
            "timestamp": time.time(),
            "extraction_result": extraction_result,
            "extractor_stats": enhanced_extractor.get_extraction_stats(),
            "ip_rotation_stats": enhanced_extractor.ip_manager.get_rotation_stats()
        }
        
        # Try to detect blocking
        if extraction_result.get("success"):
            html_content = extraction_result.get("data", {}).get("extraction_metadata", {}).get("html_length", 0)
            debug_info["content_analysis"] = {
                "html_length": html_content,
                "appears_blocked": html_content < 1000,
                "quality_score": extraction_result.get("quality_score", 0.0)
            }
        
        return debug_info
        
    except Exception as e:
        logger.error(f"❌ Debug extraction failed for {url}: {e}")
        return {
            "url": url,
            "error": str(e),
            "timestamp": time.time(),
            "success": False
        }
