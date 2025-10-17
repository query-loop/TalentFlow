from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid

from app.agents.parser_agent import extract_profile_from_text
from app.agents.skill_normalizer import normalize_skills
from app import ingest
from app.chroma_client import ChromaClient
from app.agents.resume_generator import generate_resume
from app.agents.bullet_optimizer import optimize_experience_bullets
from app.agents.ats_formatter import format_txt, format_docx
from app.agents.scorer import score_profile

router = APIRouter()


class AgentsV1In(BaseModel):
    jd: Optional[str] = Field(None, description="Job description text (string)")
    resume: Optional[str] = Field(None, description="Candidate resume text (string)")
    jd_ref: Optional[str] = Field(None, description="Reference to JD (file:// or http(s)://)")
    resume_ref: Optional[str] = Field(None, description="Reference to resume (file:// or http(s)://)")


class AgentsV1Out(BaseModel):
    parsed_profile: Dict[str, Any]
    normalized_skills: Dict[str, Any]
    generated_resume: str
    optimized_bullets: list
    txt: str
    docx_bytes_len: int
    score: Dict[str, Any]


@router.post("/v1/run", response_model=AgentsV1Out, summary="Run full agents pipeline (parse->generate->score)")
async def run_agents(
    payload: AgentsV1In = None,
    jd_file: UploadFile | None = File(None),
    resume_file: UploadFile | None = File(None),
):
    """Accepts JSON body (jd/resume or refs) or multipart file uploads (jd_file/resume_file).

    File uploads take precedence over inline text/ref.
    """
    # Normalize payload if None
    if payload is None:
        payload = AgentsV1In()

    # If files provided, extract their text
    from app.utils.fetcher import extract_text_from_bytes

    resume_text = None
    jd_text = None

    if resume_file is not None:
        try:
            data = await resume_file.read()
            resume_text = extract_text_from_bytes(data, filename=resume_file.filename or None, content_type=resume_file.content_type or None)
        finally:
            await resume_file.close()

    if jd_file is not None:
        try:
            data = await jd_file.read()
            jd_text = extract_text_from_bytes(data, filename=jd_file.filename or None, content_type=jd_file.content_type or None)
        finally:
            await jd_file.close()

    # fallback to inline or referenced text
    # Validate input presence below after resolving refs
    # Fetch resume text from ref if still missing
    if not resume_text:
        resume_text = payload.resume
        if not resume_text and payload.resume_ref:
            resume_text = ingest.fetch_text(payload.resume_ref)

    # Fetch JD text from ref if still missing
    if not jd_text:
        jd_text = payload.jd
        if not jd_text and payload.jd_ref:
            jd_text = ingest.fetch_text(payload.jd_ref)

    # Validate input after attempts
    if not resume_text or not jd_text:
        raise HTTPException(status_code=400, detail="Provide resume (text, file, or ref) and jd (text, file, or ref)")

    # Parse resume
    parsed = extract_profile_from_text(resume_text)

    # Normalize skills (ensure the response is a dict for the OpenAPI response model)
    skills = parsed.get("skills", []) or []
    normalized = normalize_skills(skills)
    # normalize_skills may return a list or None; coerce to a dict to match AgentsV1Out
    if normalized is None:
        normalized = {}
    elif isinstance(normalized, list):
        normalized = {"skills": normalized}

    # Ingest into vector DB for retrieval (use generated uuid as candidate id)
    candidate_id = f"cand-{uuid.uuid4().hex[:8]}"
    c = ChromaClient().get_collection()
    try:
        ingest.ingest_candidate(candidate_id, resume_text, collection=c)
    except Exception:
        # non-fatal: continue even if ingest fails
        pass

    # Generate resume (default model set to deepseek)
    default_model = "deepseek/DeepSeek-R1-0528"
    generated = generate_resume(parsed, query=jd_text, top_k=5, llm=default_model, collection=c)

    # Optimize bullets (use experience list or generated resume)
    exp_list = parsed.get("experience") or [generated]
    bullets = optimize_experience_bullets(exp_list)

    # Format outputs
    txt = format_txt(parsed, bullets)
    docx = format_docx(parsed, bullets)

    # Score profile against JD
    score = score_profile(parsed, {"description": jd_text, "top_keywords": []})

    return {
        "parsed_profile": parsed,
        "normalized_skills": normalized,
        "generated_resume": generated,
        "optimized_bullets": bullets,
        "txt": txt,
        "docx_bytes_len": len(docx),
        "score": score,
    }
