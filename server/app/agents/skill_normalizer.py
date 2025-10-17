"""Skill Normalizer Agent

Maps free-text skill mentions to a canonical skill ontology. Prefer using
sentence-transformers embeddings for semantic matching when available. Falls
back to fuzzy string matching when the heavy model deps are absent.

Exports: SkillNormalizer class with `normalize(skills: List[str]) -> List[dict]`
which returns list of {input, canonical, score}.
"""
from __future__ import annotations

from typing import List, Dict, Optional
import logging
import math

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _HAS_ST = True
except Exception:
    SentenceTransformer = None
    np = None
    _HAS_ST = False

from difflib import get_close_matches

logger = logging.getLogger(__name__)

# A tiny canonical skill list for demo — replace with O*NET/ESCO dataset in prod
CANONICAL_SKILLS = [
    "Python",
    "Java",
    "SQL",
    "AWS",
    "Docker",
    "Kubernetes",
    "Machine Learning",
    "Data Analysis",
    "Project Management",
]


class SkillNormalizer:
    def __init__(self, model_name: Optional[str] = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._canonical_emb = None
        if _HAS_ST and model_name:
            try:
                self._model = SentenceTransformer(model_name)
                self._canonical_emb = self._model.encode(CANONICAL_SKILLS, convert_to_numpy=True)
            except Exception as e:
                logger.exception("Failed to load sentence-transformers model; falling back")
                self._model = None
                self._canonical_emb = None

    def normalize(self, skills: List[str]) -> List[Dict]:
        results: List[Dict] = []
        if self._model and self._canonical_emb is not None:
            # embedding-based matching
            try:
                emb = self._model.encode(skills, convert_to_numpy=True)
                for i, s in enumerate(skills):
                    vec = emb[i]
                    sims = np.dot(self._canonical_emb, vec) / (
                        np.linalg.norm(self._canonical_emb, axis=1) * (np.linalg.norm(vec) + 1e-12)
                    )
                    idx = int(np.argmax(sims))
                    score = float(sims[idx])
                    results.append({"input": s, "canonical": CANONICAL_SKILLS[idx], "score": score})
                return results
            except Exception:
                logger.exception("Embedding match failed, falling back to fuzzy")

        # fallback: fuzzy string matching
        for s in skills:
            matches = get_close_matches(s, CANONICAL_SKILLS, n=1, cutoff=0.5)
            if matches:
                results.append({"input": s, "canonical": matches[0], "score": 1.0})
            else:
                # try simple substring match
                found = None
                for c in CANONICAL_SKILLS:
                    if s.lower() in c.lower() or c.lower() in s.lower():
                        found = c
                        break
                if found:
                    results.append({"input": s, "canonical": found, "score": 0.8})
                else:
                    results.append({"input": s, "canonical": None, "score": 0.0})

        return results


def normalize_skills(skills: List[str], model_name: Optional[str] = None) -> List[Dict]:
    sn = SkillNormalizer(model_name=model_name)
    return sn.normalize(skills)
