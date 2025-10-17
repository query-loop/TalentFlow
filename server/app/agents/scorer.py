"""Scorer Agent

Computes a score for a candidate profile/resume against a job posting using:
- embedding similarity (using `embedder`)
- keyword coverage (job keywords vs profile skills and text)
- ATS parse checks (presence of key fields)

Returns a dictionary with component scores and an aggregate score in [0,1].
"""
from __future__ import annotations

from typing import Dict, Any, List
import math
from app.agents.embedder import embed_texts


def _cosine(a: List[float], b: List[float]) -> float:
    da = sum(x * x for x in a) ** 0.5
    db = sum(x * x for x in b) ** 0.5
    if da == 0 or db == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (da * db)


def _keyword_coverage(keywords: List[str], profile_text: str, skills: List[str]) -> float:
    # case-insensitive match
    pt = profile_text.lower()
    sset = set([s.lower() for s in skills])
    hits = 0
    for k in keywords:
        kl = k.lower()
        if kl in pt or kl in sset:
            hits += 1
    return hits / max(1, len(keywords))


def _ats_checks(profile: Dict[str, Any]) -> float:
    # simple checks: name, email, skills
    score = 0
    total = 3
    if profile.get("name"):
        score += 1
    if profile.get("email"):
        score += 1
    if profile.get("skills"):
        score += 1
    return score / total


def score_profile(profile: Dict[str, Any], job: Dict[str, Any], embed_model: str | None = None) -> Dict[str, Any]:
    """Compute component scores and an aggregate score.

    job: expects keys `text` and `keywords` (list).
    profile: expects `raw_text` and `skills` and may include `name`/`email`.
    """
    profile_text = profile.get("raw_text", "")
    job_text = job.get("text", "")
    keywords = job.get("keywords", [])

    # embeddings
    p_emb = embed_texts([profile_text], model_name=embed_model)[0]
    j_emb = embed_texts([job_text], model_name=embed_model)[0]
    emb_sim = _cosine(p_emb, j_emb)

    kw_cov = _keyword_coverage(keywords, profile_text, profile.get("skills", []))
    ats = _ats_checks(profile)

    # aggregate: weighted sum
    agg = 0.5 * emb_sim + 0.3 * kw_cov + 0.2 * ats
    return {"embedding": emb_sim, "keyword_coverage": kw_cov, "ats": ats, "aggregate": agg}
