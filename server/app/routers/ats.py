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
    # naive mock based on text overlap
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
