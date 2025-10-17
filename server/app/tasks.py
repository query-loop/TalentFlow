from __future__ import annotations

from app.celery_app import celery_app
from app import ingest
from app import chroma_client
from app import storage
from app.agents.parser_agent import extract_profile_from_text
import logging
import json

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def ingest_resume_task(self, candidate_id: str, resume_text: str, metadata: dict | None = None) -> dict:
    try:
        client = chroma_client.ChromaClient()
        collection = client.get_collection()
        count = ingest.ingest_candidate(candidate_id, resume_text, metadata=metadata or {"source": "celery_task"}, collection=collection)
        # persist chroma if available
        try:
            client.persist()
        except Exception:
            pass
        return {"ok": True, "chunks_indexed": count}
    except Exception as e:
        logger.exception("Ingest task failed")
        return {"ok": False, "error": str(e)}


@celery_app.task
def ping() -> str:
    return "pong"


@celery_app.task(bind=True)
def parse_resume_task(self, candidate_id: str, bucket: str, object_key: str, hf_model: str | None = None) -> dict:
    """Download resume bytes from MinIO, parse into structured JSON, store result, and enqueue ingest.

    Arguments:
        candidate_id: unique candidate identifier
        bucket: minio bucket name where resume is stored
        object_key: object key (path) to resume bytes
        hf_model: optional HF model name to use for parsing
    """
    try:
        client = storage.get_client()
        # download object bytes
        data = storage.download_bytes(object_key, client=client, bucket=bucket)
        if data is None:
            raise RuntimeError("Failed to download resume bytes from storage")
        text = data.decode("utf-8", errors="ignore")

        # parse
        parsed = extract_profile_from_text(text, hf_model=hf_model)

        # store parsed JSON back to MinIO under parsed/{candidate_id}.json
        parsed_key = f"parsed/{candidate_id}.json"
        storage.upload_bytes(json.dumps(parsed).encode("utf-8"), parsed_key, content_type="application/json", client=client, bucket=bucket)

        # trigger ingest task (index full resume text into chroma)
        ingest_job = ingest_resume_task.delay(candidate_id, text, metadata={"source": "parse_resume_task"})

        return {"ok": True, "parsed_key": parsed_key, "ingest_task_id": getattr(ingest_job, 'id', None)}
    except Exception as e:
        logger.exception("parse_resume_task failed")
        return {"ok": False, "error": str(e)}
