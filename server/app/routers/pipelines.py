from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.utils.contracts import validate_against
from app.models import SessionLocal, Pipeline as PipelineModel
from sqlalchemy import select
from cachetools import TTLCache
import json
from .generate import generate_resume, GenerateRequest
from .jd import extract_jd
from .keywords import extract_keywords, KeywordsRequest
from .ats import ats_score, ATSRequest

router = APIRouter()

# canonical status keys for v1 pipelines
ORDER = ["extract", "generate", "keywords", "ats", "export", "save"]

class Statuses(BaseModel):
    extract: str
    generate: str
    keywords: str
    ats: str
    export: str
    save: str

class Pipeline(BaseModel):
    id: str
    name: str
    createdAt: int
    company: Optional[str] = None
    jdId: Optional[str] = None
    resumeId: Optional[str] = None
    statuses: Statuses

class PipelineCreate(BaseModel):
    name: str
    company: Optional[str] = None
    jdId: Optional[str] = None
    resumeId: Optional[str] = None

class PipelinePatch(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    jdId: Optional[str] = None
    resumeId: Optional[str] = None
    # allow partial updates for statuses
    statuses: Optional[Dict[str, str]] = None

class RunResult(BaseModel):
    pipeline: "Pipeline"
    log: List[str]

# Simple in-process caches (invalidate on writes)
_CACHE_GET = TTLCache(maxsize=1024, ttl=15)  # 15s cache for individual items
_CACHE_LIST = TTLCache(maxsize=1, ttl=10)    # 10s cache for list


def _to_pydantic(row: PipelineModel) -> Pipeline:
    raw = json.loads(row.statuses_json or "{}")
    # Some legacy rows might store nested {"statuses": {...}} or other content (e.g., artifacts)
    data = raw.get("statuses", raw) if isinstance(raw, dict) else {}
    # Backfill missing keys with 'pending' to keep response stable when legacy/incomplete rows exist
    statuses = {k: (data.get(k, "pending") if isinstance(data, dict) else "pending") for k in ORDER}
    return Pipeline(
        id=row.id,
        name=row.name,
        createdAt=row.created_at_ms,
        company=row.company,
        jdId=row.jd_id,
        resumeId=row.resume_id,
        statuses=Statuses(**statuses),
    )


def _invalidate_caches():
    _CACHE_GET.clear()
    _CACHE_LIST.clear()

def _ensure_single_active(statuses: Dict[str, str]) -> Dict[str, str]:
    order = ["extract","generate","keywords","ats","export","save"]
    out = dict(statuses)
    first_pending = next((k for k in order if out.get(k) != "complete"), None)
    for k in order:
        out[k] = "complete" if out.get(k) == "complete" else "pending"
    if first_pending:
        out[first_pending] = "active"
    return out

@router.get("", response_model=List[Pipeline])
async def list_pipelines() -> List[Pipeline]:
    if _CACHE_LIST:
        try:
            return _CACHE_LIST["list"]
        except KeyError:
            pass
    with SessionLocal() as db:
        rows = db.execute(select(PipelineModel).order_by(PipelineModel.created_at_ms.desc())).scalars().all()
    items: List[Pipeline] = []
    for r in rows:
        try:
            items.append(_to_pydantic(r))
        except Exception as e:
            # Skip malformed legacy rows to avoid 500s
            print(f"[pipelines] skipped malformed row id={getattr(r,'id', '?')}: {e}")
    _CACHE_LIST["list"] = items
    return items

@router.post("", response_model=Pipeline, status_code=201)
async def create_pipeline(body: PipelineCreate) -> Pipeline:
    import time, uuid
    pid = f"pl_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    created = int(time.time() * 1000)
    statuses = Statuses(
        extract="pending",
        generate="pending",
        keywords="pending",
        ats="pending",
        export="pending",
        save="pending",
    )
    with SessionLocal() as db:
        row = PipelineModel(
            id=pid,
            name=body.name,
            created_at_ms=created,
            company=body.company,
            jd_id=body.jdId,
            resume_id=body.resumeId,
            statuses_json=json.dumps(statuses.model_dump()),
        )
        db.add(row)
        db.commit()
    pipe = Pipeline(id=pid, name=body.name, createdAt=created, company=body.company, jdId=body.jdId, resumeId=body.resumeId, statuses=statuses)
    errors = validate_against("pipeline.json", pipe.model_dump())
    if errors:
        raise HTTPException(status_code=500, detail={"schema": "pipeline.json", "errors": errors})
    _invalidate_caches()
    return pipe

@router.get("/{id}", response_model=Pipeline)
async def get_pipeline(id: str) -> Pipeline:
    try:
        return _CACHE_GET[id]
    except KeyError:
        pass
    with SessionLocal() as db:
        row = db.get(PipelineModel, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
    item = _to_pydantic(row)
    _CACHE_GET[id] = item
    return item

@router.patch("/{id}", response_model=Pipeline)
async def patch_pipeline(id: str, body: PipelinePatch) -> Pipeline:
    with SessionLocal() as db:
        row = db.get(PipelineModel, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if body.name is not None:
            row.name = body.name
        if body.company is not None:
            row.company = body.company
        if body.jdId is not None:
            row.jd_id = body.jdId
        if body.resumeId is not None:
            row.resume_id = body.resumeId
        if body.statuses is not None:
            # Merge with existing statuses
            current = json.loads(row.statuses_json or "{}")
            if isinstance(body.statuses, dict):
                merged = {**current, **body.statuses}
            else:
                merged = current
            row.statuses_json = json.dumps(merged)
        db.add(row)
        db.commit()
        db.refresh(row)
    _invalidate_caches()
    return _to_pydantic(row)

@router.post("/{id}/run", response_model=RunResult)
async def run_pipeline(id: str) -> RunResult:
    """Run the pipeline end-to-end across sub-tools, updating step statuses."""
    log: List[str] = []
    with SessionLocal() as db:
        row = db.get(PipelineModel, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        # Initialize statuses
        current = json.loads(row.statuses_json or "{}") or {
            "extract":"pending","generate":"pending","keywords":"pending","ats":"pending","export":"pending","save":"pending"
        }
        current = _ensure_single_active(current)
        row.statuses_json = json.dumps(current)
        db.add(row); db.commit(); db.refresh(row)

        # Step: extract
        try:
            current = json.loads(row.statuses_json)
            current["extract"] = "active"
            row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
            if row.jd_id:
                ejd = await extract_jd(row.jd_id)
                log.append(f"extract: ok title={ejd.title}")
            else:
                log.append("extract: skipped (no jdId)")
            current["extract"] = "complete"
            current = _ensure_single_active(current)
            row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
        except Exception as e:
            current["extract"] = "failed"; row.statuses_json = json.dumps(current); db.add(row); db.commit()
            log.append(f"extract: failed {e}")
            _invalidate_caches()
            return RunResult(pipeline=_to_pydantic(row), log=log)

        # Step: generate
        try:
            current = json.loads(row.statuses_json)
            current["generate"] = "active"
            row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
            job = (row.company or "") + " Software Engineer"
            _ = await generate_resume(GenerateRequest(job=job))
            log.append("generate: ok")
            current["generate"] = "complete"
            current = _ensure_single_active(current)
            row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
        except Exception as e:
            current["generate"] = "failed"; row.statuses_json = json.dumps(current); db.add(row); db.commit()
            log.append(f"generate: failed {e}")
            _invalidate_caches()
            return RunResult(pipeline=_to_pydantic(row), log=log)

        # Step: keywords
        try:
            current = json.loads(row.statuses_json)
            current["keywords"] = "active"
            row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
            _ = await extract_keywords(KeywordsRequest(jdId=row.jd_id or "jd_mock", text="Python Svelte Postgres"))
            log.append("keywords: ok")
            current["keywords"] = "complete"
            current = _ensure_single_active(current)
            row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
        except Exception as e:
            current["keywords"] = "failed"; row.statuses_json = json.dumps(current); db.add(row); db.commit()
            log.append(f"keywords: failed {e}")
            _invalidate_caches()
            return RunResult(pipeline=_to_pydantic(row), log=log)

        # Step: ats
        try:
            current = json.loads(row.statuses_json)
            current["ats"] = "active"
            row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
            _ = await ats_score(ATSRequest(text="python svelte postgres testing"))
            log.append("ats: ok")
            current["ats"] = "complete"
            current = _ensure_single_active(current)
            row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
        except Exception as e:
            current["ats"] = "failed"; row.statuses_json = json.dumps(current); db.add(row); db.commit()
            log.append(f"ats: failed {e}")
            _invalidate_caches()
            return RunResult(pipeline=_to_pydantic(row), log=log)

        # Steps: export, save (mock)
        current = json.loads(row.statuses_json)
        current["export"] = "complete"
        current = _ensure_single_active(current)
        row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
        log.append("export: ok")

        current = json.loads(row.statuses_json)
        current["save"] = "complete"
        row.statuses_json = json.dumps(current); db.add(row); db.commit(); db.refresh(row)
        log.append("save: ok")

    _invalidate_caches()
    return RunResult(pipeline=_to_pydantic(row), log=log)

@router.delete("/{id}", status_code=204)
async def delete_pipeline(id: str):
    with SessionLocal() as db:
        row = db.get(PipelineModel, id)
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        db.delete(row)
        db.commit()
    _invalidate_caches()
    return
