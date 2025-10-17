"""LLM-powered multi-source Job Description extractor.

Pipeline Stages:
1. Fetch: Retrieve HTML (simple HTTP first; optional JS rendering hook)
2. Parse: Identify main content blocks likely containing the JD
3. Clean: Remove boilerplate, nav, footer, script/style, ads, cookie banners
4. Segment: Split content into logical sections (title, responsibilities, requirements, skills)
5. LLM Extraction: Summarize & structure using prompt (pluggable model interface)
6. Validate & Normalize: Ensure required keys, normalize skills & experience
7. Return structured payload

This module avoids hard dependency on a specific LLM vendor. Provide an implementation of BaseLLMClient.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterable, Protocol, Tuple
import re
import json
import asyncio
import httpx
from bs4 import BeautifulSoup
from readability import Document

# ---------------- LLM Client Abstractions ---------------- #
class BaseLLMClient(Protocol):
    async def complete_json(self, prompt: str, schema_hint: str | None = None, max_retries: int = 2) -> Dict[str, Any]: ...

class MockLLMClient:
    async def complete_json(self, prompt: str, schema_hint: str | None = None, max_retries: int = 2) -> Dict[str, Any]:
        # Extremely naive mock - in real use invoke OpenAI, Anthropic, etc.
        return {
            "job_title": "Software Engineer",
            "main_responsibilities": ["Build scalable services", "Collaborate with product", "Review code"],
            "key_skills_and_qualifications": ["Python", "REST APIs", "PostgreSQL"],
            "experience_requirements": "3+ years professional experience",
            "other_relevant_details": "Hybrid role; equity available"
        }

# ---------------- Configuration Data Classes ------------- #
@dataclass
class FetchConfig:
    timeout: float = 25.0
    headers: Dict[str, str] = field(default_factory=lambda: {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })

@dataclass
class ExtractionResult:
    source_url: str
    raw_text: str
    cleaned_text: str
    structured: Dict[str, Any]
    model: str
    warnings: List[str] = field(default_factory=list)

# ---------------- Fetching Layer ------------------------- #
async def fetch_url(url: str, cfg: FetchConfig) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=cfg.timeout) as client:
        r = await client.get(url, headers=cfg.headers)
        r.raise_for_status()
        return r.text

# Placeholder for future JS rendering integration
async def render_js(url: str) -> Optional[str]:
    return None  # Implement with Playwright if needed

# ---------------- Parsing & Cleaning --------------------- #
BOILERPLATE_PATTERNS = [
    re.compile(p, re.I) for p in [
        r"^about (the )?company", r"^our (mission|culture)", r"cookie preferences", r"privacy policy",
        r"^follow us", r"^newsletter", r"apply now$", r"^how to apply", r"^legal disclaimer"
    ]
]

SECTION_HINTS = {
    "responsibilities": ["responsibilities", "what you will do", "you will", "your role"],
    "requirements": ["requirements", "what you bring", "you have", "qualifications"],
    "skills": ["skills", "technologies", "tech stack"],
}

SKILL_NORMALIZATION = {
    "js": "JavaScript", "node": "Node.js", "postgres": "PostgreSQL", "k8s": "Kubernetes"
}

SKILL_PATTERN = re.compile(r"\b([A-Za-z][A-Za-z0-9+.#]{1,30})\b")

COMMON_SKILLS = {
    "python","java","javascript","typescript","react","svelte","angular","vue","docker","kubernetes","k8s","aws","gcp","azure","postgres","postgresql","mysql","mongodb","redis","graphql","rest","ci","cd","ci/cd","git","linux","terraform","ansible","kafka","spark","hadoop","go","golang","ruby","php","c#","c++","scala","swift","kotlin"
}

# ---------------- Core Extractor ------------------------- #
class LLMJobExtractor:
    def __init__(self, llm: Optional[BaseLLMClient] = None, fetch_cfg: Optional[FetchConfig] = None) -> None:
        self.llm = llm or MockLLMClient()
        self.fetch_cfg = fetch_cfg or FetchConfig()

    async def extract_from_url(self, url: str) -> ExtractionResult:
        html = await self._obtain_html(url)
        raw_main, cleaned = self._extract_main_text(html)
        prompt = self._build_prompt(cleaned[:18000])  # truncate to stay in context
        structured = await self.llm.complete_json(prompt)
        structured = self._validate_and_normalize(structured, cleaned)
        return ExtractionResult(
            source_url=url,
            raw_text=raw_main,
            cleaned_text=cleaned,
            structured=structured,
            model=self.llm.__class__.__name__,
            warnings=structured.pop("_warnings", [])
        )

    async def extract_from_html(self, url: str, html: str) -> ExtractionResult:
        raw_main, cleaned = self._extract_main_text(html)
        prompt = self._build_prompt(cleaned[:18000])
        structured = await self.llm.complete_json(prompt)
        structured = self._validate_and_normalize(structured, cleaned)
        return ExtractionResult(
            source_url=url,
            raw_text=raw_main,
            cleaned_text=cleaned,
            structured=structured,
            model=self.llm.__class__.__name__,
            warnings=structured.pop("_warnings", [])
        )

    async def _obtain_html(self, url: str) -> str:
        html = await fetch_url(url, self.fetch_cfg)
        if self._looks_incomplete(html):
            rendered = await render_js(url)
            if rendered:
                return rendered
        return html

    def _looks_incomplete(self, html: str) -> bool:
        # Heuristic: very small, or contains markers of heavy client rendering
        if len(html) < 1200: return True
        if 'id="root"' in html.lower() and 'script src' not in html.lower():
            return True
        return False

    def _extract_main_text(self, html: str) -> Tuple[str, str]:
        doc = Document(html)
        main_html = doc.summary(html_partial=True)
        soup = BeautifulSoup(main_html, 'html.parser')
        for tag in soup(['script','style','nav','header','footer','aside','form','noscript']):
            tag.decompose()
        # Remove cookie & banner nodes
        for div in soup.find_all(True):
            cls = ' '.join(div.get('class', [])).lower()
            if any(k in cls for k in ['cookie','banner','subscribe','newsletter','modal']):
                div.decompose()
        text = soup.get_text('\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        filtered = [l for l in lines if not any(p.search(l) for p in BOILERPLATE_PATTERNS)]
        cleaned = self._merge_short_lines(filtered)
        return text, cleaned

    def _merge_short_lines(self, lines: List[str]) -> str:
        buf: List[str] = []
        acc = ''
        for line in lines:
            if len(line) < 60:
                if acc:
                    acc += (' ' + line)
                else:
                    acc = line
            else:
                if acc:
                    buf.append(acc)
                    acc = ''
                buf.append(line)
        if acc:
            buf.append(acc)
        return '\n'.join(buf)

    def _build_prompt(self, content: str) -> str:
        schema_hint = json.dumps({
            "job_title": "string",
            "main_responsibilities": ["string"],
            "key_skills_and_qualifications": ["string"],
            "experience_requirements": "string",
            "other_relevant_details": "string"
        }, indent=2)
        return (
            "You are an expert recruiting analyst. Extract ONLY job-relevant information from the provided text.\n"
            "Ignore company history, ads, cookie notices, unrelated disclaimers.\n"
            "Return VALID minified JSON with keys: job_title, main_responsibilities (array), "
            "key_skills_and_qualifications (array), experience_requirements (string), other_relevant_details (string).\n"
            "If a field is missing, use an empty string or empty array. Do not invent details.\n\n"
            f"TEXT:\n{content}\n\nSCHEMA_HINT:\n{schema_hint}\nOUTPUT JSON:" )

    def _validate_and_normalize(self, data: Dict[str, Any], cleaned_text: str) -> Dict[str, Any]:
        warnings: List[str] = []
        # Guarantee keys
        for k, empty in [
            ("job_title", ""),
            ("main_responsibilities", []),
            ("key_skills_and_qualifications", []),
            ("experience_requirements", ""),
            ("other_relevant_details", "")
        ]:
            if k not in data or data[k] is None:
                data[k] = empty
                warnings.append(f"filled_missing:{k}")
        # Normalize skills
        skills = data.get('key_skills_and_qualifications', [])
        norm_skills = []
        seen = set()
        for s in skills:
            if not isinstance(s, str):
                continue
            base = s.strip()
            low = base.lower()
            if low in SKILL_NORMALIZATION:
                base = SKILL_NORMALIZATION[low]
            # quick filter for plausible skill tokens in fallback
            if len(base) > 60:
                continue
            if base.lower() in seen:
                continue
            seen.add(base.lower())
            norm_skills.append(base)
        # Fallback: mine skills from cleaned text if list too small
        if len(norm_skills) < 3:
            mined = self._mine_skills(cleaned_text)
            for m in mined:
                if m.lower() not in seen:
                    norm_skills.append(m)
                    seen.add(m.lower())
                    if len(norm_skills) >= 12:
                        break
        data['key_skills_and_qualifications'] = norm_skills
        # Basic experience normalization
        exp = data.get('experience_requirements') or ''
        m = re.search(r'(\d+\+?\s*(?:years|yrs))', exp, re.I)
        if not m:
            # Try to find in text
            m2 = re.search(r'(\d+\+?\s*(?:years|yrs) of experience)', cleaned_text, re.I)
            if m2:
                data['experience_requirements'] = m2.group(1)
                warnings.append('derived_experience')
        data['_warnings'] = warnings
        return data

    def _mine_skills(self, text: str) -> List[str]:
        found = set()
        for tok in SKILL_PATTERN.findall(text):
            low = tok.lower()
            if low in COMMON_SKILLS:
                if low in SKILL_NORMALIZATION:
                    found.add(SKILL_NORMALIZATION[low])
                else:
                    # Title-case certain multi-case tokens
                    if low in {"aws","gcp","sql","git","rest","ci","cd"}:
                        found.add(low.upper())
                    else:
                        found.add(tok if any(c.isupper() for c in tok[1:]) else tok.capitalize())
            if len(found) >= 30:
                break
        return sorted(found)

# Convenience runner (manual test)
async def demo(url: str):
    extractor = LLMJobExtractor()
    result = await extractor.extract_from_url(url)
    print(json.dumps({
        "url": result.source_url,
        "structured": result.structured,
        "warnings": result.warnings
    }, indent=2))

if __name__ == "__main__":
    import asyncio, sys
    if len(sys.argv) > 1:
        asyncio.run(demo(sys.argv[1]))
    else:
        print("Usage: python llm_extractor.py <url>")
