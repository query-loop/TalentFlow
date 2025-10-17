"""Resume Generator Agent (RAG + templates)

This agent retrieves relevant chunks using the Retriever agent, builds a prompt
using a template, and calls an LLM to generate a resume. If an LLM is not
available, it falls back to a simple template-based assembler using the
retrieved chunks and parsed profile data.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.agents.retriever import Retriever
import logging

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


DEFAULT_PROMPT_TEMPLATE = """
Use the candidate profile and retrieved context to write a crisp, ATS-friendly resume.

Profile:
{profile}

Retrieved Context:
{context}

Write a resume in markdown format with sections: Summary, Experience, Skills, Education.
Keep it concise and emphasize achievements using metrics when possible.
"""


class ResumeGenerator:
    def __init__(self, embed_model: Optional[str] = None, llm: Optional[str] = None):
        self.embed_model = embed_model
        self.llm = llm

    def generate(self, profile: Dict[str, Any], query: Optional[str] = None, top_k: int = 5, collection=None) -> str:
        # use profile and retriever to build context
        retriever = Retriever(collection=collection, embed_model=self.embed_model)
        q = query or profile.get("summary", "") or profile.get("skills", "")
        if isinstance(q, list):
            q = " ".join(q)

        try:
            hits = retriever.retrieve(q, top_k=top_k)
            docs = hits.get("documents", [[]])[0]
            metadatas = hits.get("metadatas", [[]])[0]
        except Exception:
            docs = []
            metadatas = []

        context = "\n---\n".join(docs)
        prompt = DEFAULT_PROMPT_TEMPLATE.format(profile=profile, context=context)

        # Try OpenAI
        if _HAS_OPENAI and openai is not None:
            try:
                resp = openai.ChatCompletion.create(
                    model=self.llm or "gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                )
                text = resp["choices"][0]["message"]["content"].strip()
                return text
            except Exception:
                logger.exception("OpenAI generation failed, falling back to transformers/template")

        # Try transformers if available
        if _HAS_TRANSFORMERS and self.llm:
            try:
                gen = pipeline("text-generation", model=self.llm)
                out = gen(prompt, max_length=800, do_sample=False)
                return out[0]["generated_text"]
            except Exception:
                logger.exception("Transformers generation failed, falling back to template")

        # Template fallback: assemble a simple markdown resume
        lines: List[str] = []
        lines.append(f"# {profile.get('name','')}")
        if profile.get("summary"):
            lines.append("## Summary")
            lines.append(profile.get("summary"))

        if docs:
            lines.append("## Experience (extracted)")
            for d in docs[:top_k]:
                lines.append(f"- {d}")

        if profile.get("skills"):
            skills = profile.get("skills")
            if isinstance(skills, list):
                lines.append("## Skills")
                lines.append(", ".join(skills))

        if profile.get("education"):
            lines.append("## Education")
            for e in profile.get("education"):
                lines.append(f"- {e}")

        return "\n\n".join(lines)


def generate_resume(profile: Dict[str, Any], query: Optional[str] = None, top_k: int = 5, embed_model: Optional[str] = None, llm: Optional[str] = None, collection=None) -> str:
    rg = ResumeGenerator(embed_model=embed_model, llm=llm)
    return rg.generate(profile=profile, query=query, top_k=top_k, collection=collection)
