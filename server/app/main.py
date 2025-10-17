from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ats, crawl, extract, generate, jd, keywords, pipelines, pipelines_v2, extraction_test, resume, qa, library, rapidapi_jobs, scoring
from app.routers import agents
from app.routers import agents_v1
from .models import init_db, SessionLocal
from sqlalchemy import text
import logging

# Custom logging filter to reduce noise from SSE stream endpoints
class StreamEndpointFilter(logging.Filter):
    """Filter out repetitive SSE stream endpoint logs."""
    
    def filter(self, record):
        # Only filter INFO level logs from uvicorn.access
        if record.levelno == logging.INFO and hasattr(record, 'getMessage'):
            message = record.getMessage()
            # Filter out repetitive stream endpoint logs
            if '/jd/stream' in message and 'GET' in message and '200 OK' in message:
                return False
        return True

# Apply filter to uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(StreamEndpointFilter())

app = FastAPI(title="TalentFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/status")
async def status():
    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok", "version": app.version, "database": "ok" if db_ok else "error"}

app.include_router(jd.router, prefix="/api/jd", tags=["jd"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(keywords.router, prefix="/api/keywords", tags=["keywords"])
app.include_router(ats.router, prefix="/api/ats", tags=["ats"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(pipelines_v2.router, prefix="/api/pipelines-v2", tags=["pipelines-v2"])
app.include_router(rapidapi_jobs.router, prefix="/api/rapidapi-jobs", tags=["rapidapi-jobs"])
app.include_router(extraction_test.router, prefix="/api/extraction", tags=["extraction"])
app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(scoring.router, prefix="/api/scoring", tags=["scoring"])
app.include_router(qa.router, prefix="/api/qa", tags=["qa"])
app.include_router(library.router, prefix="/api/library", tags=["library"])
app.include_router(extract.router, prefix="/api/extract", tags=["extract"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(agents_v1.router, prefix="/api/agents", tags=["agents-v1"])


@app.on_event("startup")
def _startup():
    init_db()
