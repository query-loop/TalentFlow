from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional

router = APIRouter()

class ATSRequest(BaseModel):
    jdId: Optional[str] = None
    resumeId: Optional[str] = None
    text: Optional[str] = None

class ATSResponse(BaseModel):
    score: float
    reasons: List[str]
    sections: Dict[str, str]

@router.post("", response_model=ATSResponse)
async def ats_score(body: ATSRequest) -> ATSResponse:
    from app.agents.scorer import score_profile
    # Use real scoring if resume and jd provided
    if body.resumeId or body.text:
        profile = {"raw_text": body.text or "sample resume text"}
        job = {"text": body.text or "sample job text", "keywords": ["python", "svelte", "postgres"]}
        score_result = score_profile(profile, job)
        score = score_result.get("aggregate", 0.5) * 100
        reasons = [f"Embedding similarity: {score_result.get('embedding', 0):.2f}", 
                   f"Keyword coverage: {score_result.get('keyword_coverage', 0):.2f}"]
        sections = {"summary": f"Aggregate score: {score_result.get('aggregate', 0):.2f}", 
                    "skills": ", ".join(score_result.get("matched_keywords", []))}
        return ATSResponse(score=round(score, 2), reasons=reasons, sections=sections)
    else:
        # Fallback to mock
        import re
        jd_text = body.text or "python svelte postgres testing leadership"
        resume_text = jd_text.replace("leadership", "teamwork")
        resume_words = set(re.findall(r"\w+", resume_text.lower()))
        jd_words = set(re.findall(r"\w+", jd_text.lower()))
        overlap = len(resume_words & jd_words)
        score = round(min(100.0, (overlap / max(1, len(jd_words))) * 100.0), 2)
        reasons = ["Good keyword overlap", "Experience matches requirements"]
        sections = {"summary": "Strong fit", "skills": ", ".join(sorted(resume_words & jd_words))}
        return ATSResponse(score=score, reasons=reasons, sections=sections)
