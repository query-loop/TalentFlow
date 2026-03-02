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
    # Best-effort fetch + quick extraction so frontend can use the JD immediately.
    import time, urllib.parse
    parsed = urllib.parse.urlparse(str(body.url))
    source = str(body.url)
    description_raw = f"Job description fetched from {source} (mock)."
    extracted = None

    try:
        import re
        import httpx
        from bs4 import BeautifulSoup

        # fetch with a short timeout and simple headers
        r = httpx.get(source, timeout=5.0, headers={"User-Agent": "talentflow-bot/1.0"})
        if r.status_code != 200:
            # non-200: treat as quick failure and provide minimal extracted info
            extracted = None
            raise RuntimeError(f"Non-200 status: {r.status_code}")
        if r.status_code == 200:
            # try to extract visible text quickly
            soup = BeautifulSoup(r.text, "html.parser")
            # remove script/style
            for s in soup(["script", "style", "noscript"]):
                s.extract()

            # Prefer extracting structured sections from headings and lists when available
            def extract_sections(soup):
                sections = {}
                # Look for heading tags and pull following sibling lists/paras
                for htag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                    key = htag.get_text(separator=" ").strip()
                    if not key:
                        continue
                    # Collect following siblings until next heading
                    items = []
                    for sib in htag.find_next_siblings():
                        if sib.name and sib.name.startswith('h'):
                            break
                        # capture list items
                        if sib.name == 'ul' or sib.name == 'ol':
                            for li in sib.find_all('li'):
                                txt = li.get_text(separator=' ').strip()
                                if txt:
                                    items.append(txt)
                        else:
                            txt = sib.get_text(separator=' ').strip()
                            if txt:
                                # split lines to pick dense lines
                                for ln in txt.splitlines():
                                    ln = ln.strip()
                                    if ln:
                                        items.append(ln)
                    if items:
                        sections[key.lower()] = items

                # fallback: find elements with class names indicating job description
                for cls in ["job-description", "description", "job-desc", "jd", "details"]:
                    el = soup.find(class_=lambda v: v and cls in v)
                    if el:
                        txt = el.get_text(separator='\n').strip()
                        if txt:
                            sections.setdefault('description', []).append(txt)

                return sections

            sections = extract_sections(soup)

            # Raw collapsed text for general storage
            text = soup.get_text(separator="\n")
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            description_raw = "\n".join(lines[:400])

            # title candidates
            title = None
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            # also check largest h1/h2
            if not title:
                h = soup.find(['h1', 'h2'])
                if h and h.get_text():
                    title = h.get_text().strip()

            # company heuristics: meta og:site_name or parsed hostname
            company = None
            og = soup.find('meta', property='og:site_name') or soup.find('meta', attrs={'name': 'og:site_name'})
            if og and og.get('content'):
                company = og.get('content')
            else:
                company = parsed.hostname or None

            # helper to pick section by heuristics
            def find_section(keys):
                for k in keys:
                    for sk in sections:
                        if k in sk:
                            return sections[sk]
                return []

            responsibilities = find_section(['responsibil', "what you'll do", 'what we do', 'duties', 'responsibilities'])
            requirements = find_section(['require', 'qualificat', 'must have', 'you should', 'you have'])
            skills = find_section(['skill', 'technology', 'tech stack', 'stack', 'skills'])

            # If skills not found, attempt to extract from requirements lines by splitting commas
            if not skills and requirements:
                candidates = []
                for ln in requirements:
                    # split common separators
                    for part in re.split(r'[;,–\-\|]', ln):
                        part = part.strip()
                        if 2 <= len(part) <= 40 and any(c.isalpha() for c in part):
                            candidates.append(part)
                # dedupe and take top 20
                seen = []
                for c in candidates:
                    if c.lower() not in [s.lower() for s in seen]:
                        seen.append(c)
                skills = seen[:20]

            # Experience years
            experience_years = None
            m = re.search(r'(\d+)\+?\s*(?:years|yrs)\s*(?:of)?\s*(?:experience)?', text, flags=re.I)
            if m:
                try:
                    experience_years = int(m.group(1))
                except Exception:
                    experience_years = None

            # Seniority
            seniority = None
            if re.search(r'\b(senior|sr\.?|lead|principal|staff)\b', text, flags=re.I):
                seniority = 'Senior'
            elif re.search(r'\b(junior|jr\.?|entry)\b', text, flags=re.I):
                seniority = 'Junior'
            elif re.search(r'\b(mid|mid-level|intermediate)\b', text, flags=re.I):
                seniority = 'Mid'

            # normalize lists: ensure lists of strings
            def norm_list(lst):
                return [str(x).strip() for x in lst if x and str(x).strip()][:50]

            extracted = {
                'title': title,
                'company': company,
                'location': None,
                'experienceYears': experience_years,
                'seniority': seniority,
                'skills': norm_list(skills),
                'responsibilities': norm_list(responsibilities),
                'requirements': norm_list(requirements),
                'raw': description_raw,
                'when': int(time.time() * 1000),
            }
    except Exception:
        # best-effort — on any failure return a minimal extracted structure
        # so callers (frontend) can proceed without blocking on external fetch.
        try:
            import urllib.parse as _up
            path = (_up.urlparse(source).path or '').strip('/')
            title_guess = path.split('/')[-1].replace('-', ' ').replace('_', ' ') if path else parsed.hostname
        except Exception:
            title_guess = parsed.hostname or 'Job'
        extracted = {
            'title': title_guess,
            'company': parsed.hostname or None,
            'location': None,
            'experienceYears': None,
            'seniority': None,
            'skills': [],
            'responsibilities': [],
            'requirements': [],
            'raw': description_raw,
            'when': int(time.time() * 1000),
        }

    return JD(
        id="jd_" + str(int(time.time() * 1000)),
        company=(extracted.get("company") if extracted else None) if isinstance(extracted, dict) else None,
        role=(extracted.get("title") if extracted else None) if isinstance(extracted, dict) else None,
        location=None,
        sourceUrl=source,
        sourceHost=parsed.hostname or "",
        descriptionRaw=description_raw,
        extracted=extracted,
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
