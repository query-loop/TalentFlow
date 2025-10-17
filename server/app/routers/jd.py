from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

router = APIRouter()

class JDImportRequest(BaseModel):
    url: HttpUrl

class ExtractedJD(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    experienceYears: Optional[int] = None
    seniority: Optional[str] = None
    skills: List[str] = []
    responsibilities: List[str] = []
    requirements: List[str] = []
    raw: str
    when: int

class JD(BaseModel):
    id: str
    company: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None
    sourceUrl: Optional[str] = None
    sourceHost: Optional[str] = None
    descriptionRaw: str
    extracted: Optional[ExtractedJD] = None
    reference: Optional[str] = None
    createdAt: int

@router.post("/import", response_model=JD, status_code=201)
async def import_jd(body: JDImportRequest) -> JD:
    # Mocked response for scaffolding
    import time, urllib.parse
    parsed = urllib.parse.urlparse(str(body.url))
    return JD(
        id="jd_" + str(int(time.time() * 1000)),
        company=None,
        role=None,
        location=None,
        sourceUrl=str(body.url),
        sourceHost=parsed.hostname or "",
        descriptionRaw="Job description fetched from URL (mock).",
        extracted=None,
        reference=None,
        createdAt=int(time.time() * 1000),
    )

@router.post("/{id}/extract", response_model=ExtractedJD)
async def extract_jd(id: str) -> ExtractedJD:
    import time
    # Mock extraction
    return ExtractedJD(
        title="Software Engineer",
        company="Example Co",
        location="Remote",
        experienceYears=3,
        seniority="Mid",
        skills=["Python", "Svelte", "Postgres"],
        responsibilities=["Build features", "Write tests"],
        requirements=["BS CS", "3+ years exp"],
        raw="Normalized JD text...",
        when=int(time.time() * 1000),
    )
