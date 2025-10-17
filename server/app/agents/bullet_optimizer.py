"""Bullet Optimizer Agent

Rewrites raw experience text into concise, quantified bullets. Uses OpenAI or
transformers when available, otherwise a heuristic fallback that extracts
sentences and formats them as bullets.
"""
from __future__ import annotations

from typing import List, Optional
import logging
import re

try:
    import openai
    _HAS_OPENAI = True
except Exception:
    openai = None
    _HAS_OPENAI = False

try:
    from transformers import pipeline
    _HAS_TRANSFORMERS = True
except Exception:
    pipeline = None
    _HAS_TRANSFORMERS = False

logger = logging.getLogger(__name__)


DEFAULT_PROMPT = (
    "Rewrite the following experience description into 3 concise, achievement-focused bullet points. "
    "Quantify outcomes where possible. Respond as a JSON array of strings.\n\nText:\n{txt}"
)


def optimize_bullets(texts: List[str], llm: Optional[str] = None) -> List[str]:
    """Optimize a list of experience texts into bullets.

    Returns a flat list of bullet strings.
    """
    out: List[str] = []

    # Try OpenAI
    if _HAS_OPENAI and openai is not None:
        try:
            for t in texts:
                prompt = DEFAULT_PROMPT.format(txt=t)
                resp = openai.ChatCompletion.create(model=llm or "gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=300)
                content = resp["choices"][0]["message"]["content"]
                # naive attempt to parse JSON array from content
                import json

                try:
                    bullets = json.loads(content)
                except Exception:
                    # fallback to lines
                    bullets = [ln.strip("- \n") for ln in content.splitlines() if ln.strip()]
                out.extend(bullets)
            return out
        except Exception:
            logger.exception("OpenAI bullet optimization failed, falling back")

    # Try transformers
    if _HAS_TRANSFORMERS and llm:
        try:
            gen = pipeline("text2text-generation", model=llm)
            for t in texts:
                prompt = DEFAULT_PROMPT.format(txt=t)
                res = gen(prompt, max_length=200)
                content = res[0]["generated_text"]
                out.extend([ln.strip("- \n") for ln in content.splitlines() if ln.strip()])
            return out
        except Exception:
            logger.exception("Transformers bullet generation failed, falling back")

    # Heuristic fallback: split into sentences and choose up to 3 strongest
    for t in texts:
        # naive sentence splitting
        sents = re.split(r"(?<=[.!?])\s+", t)
        # rank sentences by presence of numbers or percent/+/reduction words
        def score(s: str) -> int:
            sc = 0
            if re.search(r"\d+%", s):
                sc += 3
            if re.search(r"\d+", s):
                sc += 2
            if any(w in s.lower() for w in ["reduced", "improved", "increased", "decreased", "saved"]):
                sc += 2
            return sc

        sents_sorted = sorted(sents, key=lambda x: score(x), reverse=True)
        chosen = [s.strip() for s in sents_sorted if s.strip()][:3]
        # prefix with dash to indicate bullet
        out.extend([("- " + s) if not s.startswith("-") else s for s in chosen])

    return out


def optimize_experience_bullets(experience_texts: List[str], llm: Optional[str] = None) -> List[str]:
    return optimize_bullets(experience_texts, llm=llm)
