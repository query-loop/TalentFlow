from __future__ import annotations

"""
Enhanced job extractor with site-specific patterns and robust fallbacks.
Priority: JSON-LD -> site patterns -> microdata -> DOM/regex fallbacks.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from pathlib import Path
from urllib.parse import urlparse

from .job_sites import extract_with_site_patterns, enhance_job_data
from .ai_extractor import AIJobExtractor


class SimpleJobExtractor:
    """Minimal job extractor for server-side usage."""

    def __init__(self) -> None:
        # Common skill patterns
        self.skill_patterns = [
            r"\b(?:JavaScript|TypeScript|Python|Java|C\+\+|C#|Go|Rust|PHP|Ruby|Swift|Kotlin)\b",
            r"\b(?:React|Vue|Angular|Svelte|Node\.js|Express|Django|Flask|FastAPI|Spring)\b",
            r"\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|Git|PostgreSQL|MySQL|MongoDB)\b",
            r"\b(?:HTML|CSS|SQL|REST|GraphQL|API|CI/CD|DevOps|Agile|Scrum)\b",
        ]

        self.employment_type_map = {
            "full time": "full-time",
            "fulltime": "full-time",
            "part time": "part-time",
            "parttime": "part-time",
            "contractor": "contract",
            "consulting": "contract",
            "intern": "internship",
            "temporary": "temporary",
            "freelance": "freelance",
        }
        # Load site profiles (best-effort; optional)
        self.profiles = self._load_profiles()
        
        # Initialize AI extractor
        self.ai_extractor = AIJobExtractor()

    def _load_profiles(self) -> List[Dict[str, Any]]:
        try:
            here = Path(__file__).resolve().parent
            data = json.loads((here / 'profiles.json').read_text('utf-8'))
            return data.get('profiles') or []
        except Exception:
            return []

    def extract(self, url: str, html: str, use_ai: bool = False) -> Dict[str, Any]:
        if use_ai:
            # Use AI-powered dynamic extraction
            return self.extract_with_ai(url, html)
        
        # Priority order: JSON-LD -> site patterns -> profiles -> microdata -> DOM/regex
        json_ld = self._extract_json_ld(html)
        site_patterns = extract_with_site_patterns(url, html)
        prof_dom = self._extract_with_profile(url, html)
        microdata = self._extract_microdata(html)
        dom = self._extract_dom(html)
        regexd = self._extract_regex(html)

        field_sources: Dict[str, str] = {}
        data = self._merge(json_ld, site_patterns, prof_dom, microdata, dom, regexd, field_sources)
        
        # Enhance with post-processing
        data = enhance_job_data(data, url)

        if "source_url" not in data:
            data["source_url"] = url
        data["retrieved_at"] = datetime.now(timezone.utc).isoformat()
        data["provenance"] = {
            "extraction_method": self._primary_method(json_ld, site_patterns, prof_dom),
            "confidence_score": self._confidence(json_ld, site_patterns, prof_dom),
            "field_sources": field_sources,
            "warnings": [],
        }

        return self._validate_and_repair(data)

    def extract_with_ai(self, url: str, html: str) -> Dict[str, Any]:
        """Extract job data using AI-powered dynamic analysis."""
        try:
            # Use AI extractor for dynamic analysis
            ai_data = self.ai_extractor.extract_dynamically(url, html)
            
            # Also run traditional extraction for comparison/fallback
            traditional_data = self.extract(url, html, use_ai=False)
            
            # Merge AI results with traditional extraction (AI takes priority)
            merged_data = self._merge_ai_with_traditional(ai_data, traditional_data)
            
            # Add AI-specific metadata
            merged_data["retrieved_at"] = datetime.now(timezone.utc).isoformat()
            merged_data["provenance"] = {
                "extraction_method": "ai_dynamic_hybrid",
                "confidence_score": ai_data.get("confidence_score", 0.5),
                "ai_discovered_elements": ai_data.get("discovered_elements", 0),
                "page_structure": ai_data.get("page_structure", {}),
                "warnings": [],
            }
            
            return self._validate_and_repair(merged_data)
            
        except Exception as e:
            # Fallback to traditional extraction if AI fails
            fallback_data = self.extract(url, html, use_ai=False)
            fallback_data["provenance"]["warnings"].append(f"AI extraction failed: {str(e)}")
            fallback_data["provenance"]["extraction_method"] = "traditional_fallback"
            return fallback_data

    def _merge_ai_with_traditional(self, ai_data: Dict[str, Any], 
                                   traditional_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge AI extraction results with traditional extraction."""
        merged = traditional_data.copy()
        
        # AI data takes priority for core fields
        priority_fields = ['title', 'company', 'location', 'description', 'employment_type']
        for field in priority_fields:
            if ai_data.get(field) and (not merged.get(field) or 
                                       ai_data.get("confidence_score", 0) > 0.7):
                merged[field] = ai_data[field]
        
        # Merge lists (requirements, benefits)
        for list_field in ['requirements', 'benefits']:
            ai_items = ai_data.get(list_field, [])
            traditional_items = merged.get(list_field, [])
            
            # Combine and deduplicate
            all_items = list(traditional_items) + list(ai_items)
            unique_items = []
            seen = set()
            for item in all_items:
                if isinstance(item, str):
                    item_lower = item.lower().strip()
                    if item_lower not in seen and len(item.strip()) > 10:
                        seen.add(item_lower)
                        unique_items.append(item.strip())
            
            merged[list_field] = unique_items[:10]  # Limit to top 10
        
        # Add AI-specific fields
        merged['links'] = ai_data.get('links', {})
        merged['ai_confidence'] = ai_data.get('confidence_score', 0.0)
        
        return merged

    def _extract_with_profile(self, url: str, html: str) -> Dict[str, Any]:
        try:
            host = (urlparse(url).hostname or '').lower()
        except Exception:
            host = ''
        if not host or not self.profiles:
            return {}
        # Since we avoid external deps, emulate minimal selector matching using regex heuristics.
        # We will handle a subset: meta og:site_name, and class-based blocks.
        result: Dict[str, Any] = {}
        # Determine matching profile
        prof = None
        for p in self.profiles:
            for m in p.get('match', []):
                if m in host:
                    prof = p
                    break
            if prof:
                break
        if not prof:
            return {}
        sels = prof.get('selectors', {})
        # title
        if 'title' in sels:
            t = self._first_text_by_classes_or_tag(html, sels['title'])
            if t:
                result['title'] = t
        # company via og:site_name or class
        comp = self._meta_property_content(html, 'og:site_name')
        if not comp and 'company' in sels:
            comp = self._first_text_by_classes_or_tag(html, sels['company'])
        if comp:
            result['company'] = comp
        # location
        if 'location' in sels:
            loc = self._first_text_by_classes_or_tag(html, sels['location'])
            if loc:
                result['location'] = loc
        # description
        if 'description' in sels:
            desc = self._first_block_by_classes_or_tag(html, sels['description'])
            if desc and len(desc) > 50:
                result['description'] = desc
        return result

    def _meta_property_content(self, html: str, prop: str) -> Optional[str]:
        pat = rf"<meta[^>]*property=[\"']{re.escape(prop)}[\"'][^>]*content=[\"']([^\"']+)[\"']"
        m = re.search(pat, html, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def _first_text_by_classes_or_tag(self, html: str, selector_list: str) -> Optional[str]:
        # selector_list: comma-separated CSS-like selectors; support: h1, .class, tag.class
        selectors = [s.strip() for s in selector_list.split(',') if s.strip()]
        for sel in selectors:
            if sel.startswith('meta['):
                # handled by _meta_property_content elsewhere
                continue
            # Convert simple .class or tag.class to regex
            if sel.startswith('.'):
                cls = sel[1:].replace('.', ' ')
                pat = rf"<[^>]*class=[\"'][^\"']*{re.escape(cls)}[^\"']*[\"'][^>]*>([^<]+)</[^>]+>"
            else:
                parts = sel.split('.')
                tag = parts[0]
                cls = ' '.join(parts[1:]) if len(parts) > 1 else ''
                if cls:
                    pat = rf"<{tag}[^>]*class=[\"'][^\"']*{re.escape(cls)}[^\"']*[\"'][^>]*>([^<]+)</{tag}>"
                else:
                    pat = rf"<{tag}[^>]*>([^<]+)</{tag}>"
            m = re.search(pat, html, re.IGNORECASE)
            if m and m.group(1).strip():
                return m.group(1).strip()
        return None

    def _first_block_by_classes_or_tag(self, html: str, selector_list: str) -> Optional[str]:
        selectors = [s.strip() for s in selector_list.split(',') if s.strip()]
        for sel in selectors:
            if sel.startswith('.'):
                cls = sel[1:].replace('.', ' ')
                pat = rf"<[^>]*class=[\"'][^\"']*{re.escape(cls)}[^\"']*[\"'][^>]*>(.*?)</[^>]+>"
            else:
                parts = sel.split('.')
                tag = parts[0]
                cls = ' '.join(parts[1:]) if len(parts) > 1 else ''
                if cls:
                    pat = rf"<{tag}[^>]*class=[\"'][^\"']*{re.escape(cls)}[^\"']*[\"'][^>]*>(.*?)</{tag}>"
                else:
                    pat = rf"<{tag}[^>]*>(.*?)</{tag}>"
            m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
            if m:
                text = re.sub(r"<[^>]+>", " ", m.group(1))
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    return text
        return None

    def _extract_json_ld(self, html: str) -> Dict[str, Any]:
        script_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, html, re.IGNORECASE | re.DOTALL)
        for content in scripts:
            try:
                data = json.loads(content.strip())
            except Exception:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return self._parse_jobposting(item)
        return {}

    def _parse_jobposting(self, d: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if d.get("title"):
            out["title"] = str(d["title"]).strip()
        org = d.get("hiringOrganization") or d.get("hiringorganization")
        if isinstance(org, dict):
            name = org.get("name") or org.get("@name") or org.get("legalName") or org.get("alternateName")
            if name:
                out["company"] = str(name).strip()
        elif isinstance(org, str):
            out["company"] = org.strip()

        jl = d.get("jobLocation") or d.get("joblocation")
        if jl:
            loc = self._location_from_joblocation(jl)
            if loc:
                out["location"] = loc

        emp = d.get("employmentType")
        if emp:
            out["employment_type"] = self._normalize_employment_type(str(emp))

        if d.get("datePosted"):
            out["posted_date"] = self._normalize_date(str(d["datePosted"]))

        if d.get("description"):
            out["description"] = str(d["description"]).strip()
        return out

    def _location_from_joblocation(self, jl: Any) -> Optional[str]:
        if isinstance(jl, list) and jl:
            jl = jl[0]
        if isinstance(jl, dict):
            addr = jl.get("address") or jl.get("@address")
            if isinstance(addr, dict):
                parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
                parts = [p for p in parts if p]
                if parts:
                    return ", ".join(map(str, parts))
            name = jl.get("name")
            if name:
                return str(name)
        return None

    def _extract_microdata(self, html: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        pat = r'<[^>]*itemprop=["\']([^"\']*)["\'][^>]*(?:content=["\']([^"\']*)["\']|>([^<]*))'
        for prop, content_attr, text_content in re.findall(pat, html, re.IGNORECASE):
            content = (content_attr or text_content or "").strip()
            if not content:
                continue
            if prop == "title":
                result["title"] = content
            elif prop == "hiringOrganization":
                result["company"] = content
            elif prop == "jobLocation":
                result["location"] = content
            elif prop == "employmentType":
                result["employment_type"] = self._normalize_employment_type(content)
            elif prop == "datePosted":
                result["posted_date"] = self._normalize_date(content)
            elif prop == "description":
                result["description"] = content
        return result

    def _extract_dom(self, html: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        # title
        for pat in [
            r'<h1[^>]*class=["\'][^"\']*(?:job|title)[^"\']*["\'][^>]*>([^<]+)</h1>',
            r'<h1[^>]*>([^<]+)</h1>',
            r'<title>([^<|]+)'
        ]:
            m = re.search(pat, html, re.IGNORECASE)
            if m and m.group(1).strip():
                result["title"] = m.group(1).strip()
                break

        # company
        for pat in [
            r'<[^>]*class=["\'][^"\']*company[^"\']*["\'][^>]*>([^<]+)</[^>]*>',
            r'<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)["\']',
            r'<[^>]*class=["\'][^"\']*employer[^"\']*["\'][^>]*>([^<]+)</[^>]*>'
        ]:
            m = re.search(pat, html, re.IGNORECASE)
            if m and m.group(1).strip():
                result["company"] = m.group(1).strip()
                break

        # location
        for pat in [
            r'<[^>]*class=["\'][^"\']*location[^"\']*["\'][^>]*>([^<]+)</[^>]*>',
            r'<[^>]*data-testid=["\'][^"\']*location[^"\']*["\'][^>]*>([^<]+)</[^>]*>'
        ]:
            m = re.search(pat, html, re.IGNORECASE)
            if m and m.group(1).strip():
                result["location"] = m.group(1).strip()
                break

        # description
        for pat in [
            r'<[^>]*class=["\'][^"\']*(?:job-desc|description)[^"\']*["\'][^>]*>(.*?)</[^>]*>',
            r'<main[^>]*>(.*?)</main>',
            r'<article[^>]*>(.*?)</article>'
        ]:
            m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
            if m:
                desc = re.sub(r"<[^>]+>", " ", m.group(1))
                desc = re.sub(r"\s+", " ", desc).strip()
                if len(desc) > 50:
                    result["description"] = desc
                    break
        return result

    def _extract_regex(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if not text:
            return result
        # skills
        skills = set()
        for pat in self.skill_patterns:
            for m in re.findall(pat, text, re.IGNORECASE):
                if m:
                    skills.add(m.strip())
        if skills:
            result["skills"] = list(skills)[:50]

        # salary (guard against dates)
        salary_pat = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K|thousand)?\s*(?:-|to)\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K|thousand)?\s*(?:per\s+)?(year|annual|hour|month)?'
        sm = re.search(salary_pat, text, re.IGNORECASE)
        if sm:
            raw = sm.group(0)
            has_hint = (
                ("$" in raw)
                or ("usd" in raw.lower())
                or ("k" in raw.lower())
                or re.search(r"\b(per|hour|year|annual|month|salary|compensation|pay)\b", raw, re.IGNORECASE)
            )
            if has_hint:
                try:
                    min_sal = float(sm.group(1).replace(",", ""))
                    max_sal = float(sm.group(2).replace(",", ""))
                    period = sm.group(3) or "yearly"
                    if "k" in raw.lower():
                        min_sal *= 1000
                        max_sal *= 1000
                    result["salary"] = {
                        "min": min_sal,
                        "max": max_sal,
                        "currency": "USD",
                        "period": "yearly" if period and period.lower() in ["year", "annual"] else ("hourly" if period and period.lower() == "hour" else "yearly"),
                    }
                except Exception:
                    pass
        return result

    def _merge(self, a: Dict, b: Dict, c: Dict, d: Dict, e: Dict, f: Dict, field_sources: Dict[str, str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for src, name in [(a, "json-ld"), (b, "site-patterns"), (c, "profiles"), (d, "microdata"), (e, "dom"), (f, "regex")]:
            for k, v in src.items():
                if k in ["responsibilities", "qualifications", "skills", "benefits"]:
                    if v:
                        out.setdefault(k, [])
                        for item in (v if isinstance(v, list) else [v]):
                            if item not in out[k]:
                                out[k].append(item)
                        field_sources[k] = field_sources.get(k, name)
                else:
                    if v is not None and k not in out:
                        out[k] = v
                        field_sources[k] = name
        return out

    def _primary_method(self, a: Dict, b: Dict, c: Dict) -> str:
        if a:
            return "json-ld"
        if b:
            return "site-patterns"
        if c:
            return "profiles"
        return "fallback"

    def _confidence(self, a: Dict, b: Dict, c: Dict) -> float:
        if a:
            return 0.95
        if b:
            return 0.90
        if c:
            return 0.75
        return 0.5

    def _normalize_employment_type(self, emp_type: str) -> Optional[str]:
        s = (emp_type or "").lower().strip()
        if not s:
            return None
        return self.employment_type_map.get(
            s,
            s if s in ["full-time", "part-time", "contract", "temporary", "internship", "freelance"] else None,
        )

    def _normalize_date(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt).date().isoformat()
            except Exception:
                continue
        return None

    def _validate_and_repair(self, data: Dict[str, Any]) -> Dict[str, Any]:
        warnings = data.get("provenance", {}).get("warnings", [])
        if not data.get("title"):
            data["title"] = "Job Opening"
            warnings.append("Title missing, used default")
        if not data.get("company"):
            try:
                hn = (urlparse(data.get("source_url", "")).hostname or "").split(".")[0]
                data["company"] = hn.title() if hn else "Unknown Company"
                warnings.append("Company guessed from hostname")
            except Exception:
                data["company"] = "Unknown Company"
                warnings.append("Company missing, used default")
        if not data.get("description") or len(str(data.get("description"))) < 50:
            data["description"] = f"Job opening at {data.get('company', 'Company')} for {data.get('title', 'Role')}"
            warnings.append("Description missing, used minimal default")
        if "provenance" in data:
            data["provenance"]["warnings"] = warnings
        return data
