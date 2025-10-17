"""Parser agent: extract structured candidate profile from raw resume text.

This module provides a ParserAgent class that uses a Hugging Face / transformers
model when available, and falls back to a deterministic rule-based extractor
for environments without heavy model dependencies (CI/dev).

The agent returns a dict with keys like: name, email, phone, summary, skills,
experience (list), education (list), and raw_text.
"""
from __future__ import annotations

import re
import json
from typing import Dict, Any, List, Optional

try:
    # transformers is optional; parser will gracefully fall back if unavailable
    from transformers import pipeline
    _HAS_TRANSFORMERS = True
except Exception:
    pipeline = None
    _HAS_TRANSFORMERS = False


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{6,}\d")


class ParserAgent:
    def __init__(self, hf_model: Optional[str] = None):
        """Initialize the parser agent.

        If transformers is available and hf_model is provided, a text2text-generation
        pipeline will be created. Otherwise the agent will use a lightweight
        rule-based fallback extractor.
        """
        self.hf_model = hf_model
        self._nlp = None
        if _HAS_TRANSFORMERS and hf_model:
            try:
                # text2text-generation or zero-shot summarization style model
                self._nlp = pipeline("text2text-generation", model=hf_model)
            except Exception:
                # if model fails to load, fallback to rule-based
                self._nlp = None

    def parse(self, text: str) -> Dict[str, Any]:
        """Parse resume text and return structured profile."""
        if self._nlp:
            try:
                prompt = self._build_prompt(text)
                res = self._nlp(prompt, max_length=1024)
                # transformers returns a list of dicts with 'generated_text'
                generated = res[0]["generated_text"] if res and isinstance(res, list) else str(res)
                # expect JSON string from the model
                parsed = json.loads(generated)
                parsed["raw_text"] = text
                return parsed
            except Exception:
                # fallback to rule-based on any failure
                pass

        return self._rule_based_parse(text)

    def _build_prompt(self, text: str) -> str:
        # The prompt asks the model to extract fields as JSON.
        return (
            "Extract the following fields from the resume as a JSON object: name, email, phone, "
            "summary, skills (list), experience (list of {title,company,start,end,description}), "
            "education (list), and any certifications. If a field is missing, return an empty string or empty list.\n\n"
            "Resume:\n" + text + "\n\nRespond only with a valid JSON object."
        )

    def _rule_based_parse(self, text: str) -> Dict[str, Any]:
        # Very simple deterministic extraction suitable for tests/dev.
        emails = EMAIL_RE.findall(text)
        phones = PHONE_RE.findall(text)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        name = lines[0] if lines else ""

        # naive skills extraction: look for a Skills: or Skills\n block
        skills = []
        for i, ln in enumerate(lines):
            if ln.lower().startswith("skills"):
                # take the rest of the line after ':' or the next line
                parts = ln.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    skills = [s.strip() for s in parts[1].split(",") if s.strip()]
                elif i + 1 < len(lines):
                    skills = [s.strip() for s in lines[i + 1].split(",") if s.strip()]
                break

        profile = {
            "name": name,
            "email": emails[0] if emails else "",
            "phone": phones[0] if phones else "",
            "summary": "",
            "skills": skills,
            "experience": [],
            "education": [],
            "certifications": [],
            "raw_text": text,
        }
        return profile


def extract_profile_from_text(text: str, hf_model: Optional[str] = None) -> Dict[str, Any]:
    agent = ParserAgent(hf_model=hf_model)
    return agent.parse(text)
