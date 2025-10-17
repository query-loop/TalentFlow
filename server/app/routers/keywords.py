from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter()

class KeywordsRequest(BaseModel):
    jdId: str
    resumeId: str | None = None
    text: str | None = None

class KeywordsResponse(BaseModel):
    present: List[str]
    missing: List[str]
    weak: List[str]
    counts: Dict[str, int]

@router.post("", response_model=KeywordsResponse)
async def extract_keywords(body: KeywordsRequest) -> KeywordsResponse:
    # naive mock based on provided text or jdId
    import re
    text = body.text or f"JD {body.jdId} requires Python Svelte Postgres testing"
    words = re.findall(r"\b\w+\b", text.lower())
    freq: Dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    vocab = list(freq.keys())
    present = vocab[:5]
    missing = ["graphql", "docker"]
    weak = ["testing"] if "testing" in vocab else []
    return KeywordsResponse(present=present, missing=missing, weak=weak, counts=freq)
