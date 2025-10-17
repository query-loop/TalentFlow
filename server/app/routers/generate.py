from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from fastapi.responses import StreamingResponse
import asyncio
from app.utils.contracts import validate_against
from app.models import SessionLocal, GeneratedResume
from app.ai.agent import agent_generate
import json as pyjson

router = APIRouter()

class GenerateRequest(BaseModel):
    job: str
    prompt: Optional[str] = None
    resumeId: Optional[str] = None
    jdId: Optional[str] = None
    agentic: Optional[bool] = False
    resumeText: Optional[str] = None
    targetRole: Optional[str] = None

class GenerateResponse(BaseModel):
    summary: str
    skills: List[str]
    experience: List[str]
    cost: float
    tokenUsage: Dict[str, int]
    fullText: Optional[str] = None
    plan: Optional[List[str]] = None

@router.post("", response_model=GenerateResponse)
async def generate_resume(body: GenerateRequest) -> GenerateResponse:
    # Agentic mode uses LLM (if configured) with resumeText + JD reference
    if body.agentic:
        data: Dict[str, Any] = agent_generate(body.job, body.resumeText, body.targetRole)
        summary = data.get("summary") or "Tailored resume draft"
        skills = list(map(str, data.get("skills") or []))
        experience = list(map(str, data.get("experience") or []))
        full_text = data.get("updatedResume") or None
        resp = GenerateResponse(
            summary=summary,
            skills=skills,
            experience=experience,
            cost=0.001,
            tokenUsage={"prompt": 100, "completion": 200, "total": 300},
            fullText=full_text,
            plan=list(map(str, data.get("plan") or [])),
        )
    else:
        # Mocked response adhering to schema
        top_skills = [w for w in body.job.split() if w.istitle()][:5] or ["Python", "Svelte", "Postgres"]
        resp = GenerateResponse(
            summary=f"Tailored resume draft for: {body.job[:64]}...",
            skills=top_skills,
            experience=["Implemented features end-to-end", "Collaborated across teams"],
            cost=0.001,
            tokenUsage={"prompt": 100, "completion": 200, "total": 300},
        )
    # Validate against contracts/schemas/generate_response.json
    errors = validate_against("generate_response.json", resp.model_dump())
    if errors:
        raise HTTPException(status_code=500, detail={"schema": "generate_response.json", "errors": errors})
    # Persist to DB (SQLite)
    with SessionLocal() as db:
        obj = GeneratedResume(
            job=body.job,
            prompt=body.prompt,
            summary=resp.summary,
            skills=pyjson.dumps(resp.skills),
            experience=pyjson.dumps(resp.experience),
        )
        db.add(obj)
        db.commit()
    return resp

@router.post("/stream")
async def generate_stream(body: GenerateRequest):
    async def event_gen():
        # simple mock: stream partial fields of GenerateResponse as separate SSE data frames
        import json
        partials = [
            {"summary": f"Tailored resume draft for: {body.job[:64]}..."},
            {"skills": [w for w in body.job.split() if w.istitle()][:5] or ["Python", "Svelte", "Postgres"]},
            {"experience": ["Implemented features end-to-end", "Collaborated across teams"]},
            {"cost": 0.001},
            {"tokenUsage": {"prompt": 100, "completion": 200, "total": 300}},
        ]
        for item in partials:
            yield f"data: {json.dumps(item)}\n\n"
            await asyncio.sleep(0.1)
        yield "event: end\ndata: done\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/history")
async def generate_history():
    items = []
    with SessionLocal() as db:
        rows = db.query(GeneratedResume).order_by(GeneratedResume.created_at.desc()).limit(20).all()
        for r in rows:
            try:
                items.append({
                    "id": r.id,
                    "job": r.job,
                    "prompt": r.prompt,
                    "summary": r.summary,
                    "skills": pyjson.loads(r.skills or "[]"),
                    "experience": pyjson.loads(r.experience or "[]"),
                    "createdAt": r.created_at.isoformat() + "Z",
                })
            except Exception:
                continue
    return {"items": items}

