from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.agents.parser_agent import extract_profile_from_text
from app.utils.text_sanitizer import sanitize_text
from app.agents.skill_normalizer import normalize_skills
from app.agents.retriever import retrieve
from app.agents.resume_generator import generate_resume
from app.agents.bullet_optimizer import optimize_experience_bullets
from app.agents.ats_formatter import format_txt, format_docx
from app.agents.scorer import score_profile
from app.agents.feedback_loop import FeedbackLoop, FeedbackStore, Ranker
from app import ingest
from app.chroma_client import ChromaClient
from app.models_registry import list_models, try_load_model

router = APIRouter()


class TextIn(BaseModel):
    text: Optional[str] = None
    reference: Optional[str] = None


class ParseOut(BaseModel):
    profile: Dict[str, Any]


@router.post("/parse", response_model=ParseOut)
def parse_text(payload: TextIn):
    if not payload.text and not payload.reference:
        raise HTTPException(status_code=400, detail="Provide text or reference")
    text = payload.text
    if not text and payload.reference:
        text = ingest.fetch_text(payload.reference)
    # sanitize before parsing to remove control characters and normalize whitespace
    text = sanitize_text(text)
    profile = extract_profile_from_text(text)
    return {"profile": profile}


class NormalizeIn(BaseModel):
    skills: List[str]
    model: Optional[str] = None


@router.post("/normalize")
def normalize_skills_route(payload: NormalizeIn):
    return {"normalized": normalize_skills(payload.skills, model_name=payload.model)}


class IngestIn(BaseModel):
    candidate_id: str
    text: Optional[str] = None
    reference: Optional[str] = None


@router.post("/ingest")
def ingest_route(payload: IngestIn):
    c = ChromaClient().get_collection()
    if payload.text:
        cnt = ingest.ingest_candidate(payload.candidate_id, payload.text, collection=c)
    else:
        if not payload.reference:
            raise HTTPException(status_code=400, detail="text or reference required")
        cnt = ingest.ingest_from_reference(payload.candidate_id, payload.reference, collection=c)
    return {"indexed_chunks": cnt}


class RetrieveIn(BaseModel):
    query: str
    top_k: Optional[int] = 5


@router.post("/retrieve")
def retrieve_route(payload: RetrieveIn):
    c = ChromaClient().get_collection()
    res = retrieve(payload.query, top_k=payload.top_k, collection=c)
    return res


class GenerateIn(BaseModel):
    profile: Dict[str, Any]
    query: Optional[str] = None
    top_k: Optional[int] = 5
    model_id: Optional[str] = None


@router.post("/generate")
def generate_route(payload: GenerateIn):
    c = ChromaClient().get_collection()
    out = generate_resume(payload.profile, query=payload.query, top_k=payload.top_k, llm=payload.model_id, collection=c)
    return {"resume": out}


class OptimizeIn(BaseModel):
    experience: List[str]


@router.post("/optimize")
def optimize_route(payload: OptimizeIn):
    bullets = optimize_experience_bullets(payload.experience)
    return {"bullets": bullets}


class FormatIn(BaseModel):
    profile: Dict[str, Any]
    bullets: List[str]


@router.post("/format")
def format_route(payload: FormatIn):
    txt = format_txt(payload.profile, payload.bullets)
    docx = format_docx(payload.profile, payload.bullets)
    return {"txt": txt, "docx_bytes_len": len(docx)}


class ScoreIn(BaseModel):
    profile: Dict[str, Any]
    job: Dict[str, Any]


@router.post("/score")
def score_route(payload: ScoreIn):
    sc = score_profile(payload.profile, payload.job)
    return sc


class FeedbackIn(BaseModel):
    profile: Dict[str, Any]
    job: Dict[str, Any]
    label: int


@router.post("/feedback")
def feedback_route(payload: FeedbackIn):
    fb = FeedbackLoop(store=FeedbackStore(client=None), ranker=Ranker(), embed_model=None)
    key = fb.record_feedback(payload.profile, payload.job, label=payload.label)
    return {"key": key}


class OrchestrateIn(BaseModel):
    candidate_id: str
    resume_reference: Optional[str] = None
    resume_text: Optional[str] = None
    job: Dict[str, Any]
    llm_model: Optional[str] = None


@router.post("/orchestrate")
def orchestrate(payload: OrchestrateIn):
    # parse + normalize + ingest + generate + optimize + format + score
    if payload.resume_text:
        text = payload.resume_text
    elif payload.resume_reference:
        text = ingest.fetch_text(payload.resume_reference)
    else:
        raise HTTPException(status_code=400, detail="resume_text or resume_reference required")

    profile = extract_profile_from_text(text)
    profile["normalized_skills"] = normalize_skills(profile.get("skills", []), model_name=None)
    c = ChromaClient().get_collection()
    ingest.ingest_candidate(payload.candidate_id, text, collection=c)
    resume = generate_resume(profile, collection=c, llm=payload.llm_model)
    bullets = optimize_experience_bullets([resume])
    txt = format_txt(profile, bullets)
    score = score_profile(profile, payload.job)
    # store feedback hint (no label) for analytics
    return {"resume": resume, "bullets": bullets, "txt": txt, "score": score}


@router.get("/models")
def models_list():
    """List available recommended models for tasks."""
    return {"models": list_models()}


class LoadModelIn(BaseModel):
    model_id: str
    task: Optional[str] = None


@router.post("/models/load")
def load_model_route(payload: LoadModelIn):
    res = try_load_model(payload.model_id, task=payload.task)
    return res
