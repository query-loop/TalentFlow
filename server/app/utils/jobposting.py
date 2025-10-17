from __future__ import annotations

from typing import Any, Dict, Optional
import re


EMPLOYMENT_MAP = {
    "full-time": "FULL_TIME",
    "full time": "FULL_TIME",
    "part-time": "PART_TIME",
    "part time": "PART_TIME",
    "contract": "CONTRACTOR",
    "temporary": "TEMPORARY",
    "internship": "INTERN",
    "freelance": "CONTRACTOR",
}


def _parse_location(loc: Optional[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    if not loc:
        return result
    s = loc.strip()
    if re.search(r"\bremote\b", s, re.I):
        result["jobLocationType"] = "TELECOMMUTE"
        return result
    # Try City, ST pattern
    m = re.search(r"^\s*([A-Za-z .'-]{2,60})\s*,\s*([A-Z]{2})\s*$", s)
    if m:
        city, st = m.group(1).strip(), m.group(2).strip()
        result["jobLocation"] = [{
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": city,
                "addressRegion": st,
            }
        }]
        return result
    # Fallback: City, Country
    m2 = re.search(r"^\s*([A-Za-z .'-]{2,60})\s*,\s*([A-Za-z .'-]{2,60})\s*$", s)
    if m2:
        city, country = m2.group(1).strip(), m2.group(2).strip()
        result["jobLocation"] = [{
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": city,
                "addressCountry": country,
            }
        }]
        return result
    # Plain text fallback
    result["jobLocation"] = [{
        "@type": "Place",
        "address": {"@type": "PostalAddress", "addressLocality": s}
    }]
    return result


def _employment_type(s: Optional[str]) -> Optional[list[str]]:
    if not s:
        return None
    key = s.strip().lower()
    mapped = EMPLOYMENT_MAP.get(key)
    return [mapped] if mapped else None


def _base_salary(salary: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(salary, dict):
        return None
    try:
        min_v = float(salary.get("min")) if salary.get("min") is not None else None
        max_v = float(salary.get("max")) if salary.get("max") is not None else None
        currency = salary.get("currency") or "USD"
        period = (salary.get("period") or "yearly").lower()
        unit = "YEAR" if period in ("year", "yearly", "annual") else ("HOUR" if period == "hourly" else "YEAR")
        if min_v is None and max_v is None:
            return None
        value: Dict[str, Any] = {"@type": "QuantitativeValue"}
        if min_v is not None:
            value["minValue"] = min_v
        if max_v is not None:
            value["maxValue"] = max_v
        value["unitText"] = unit
        return {
            "@type": "MonetaryAmount",
            "currency": currency,
            "value": value,
        }
    except Exception:
        return None


def standardize_to_jobposting(data: Dict[str, Any]) -> Dict[str, Any]:
    """Map internal extractor output to Schema.org JobPosting."""
    title = (data.get("title") or "").strip() or None
    company = (data.get("company") or "").strip() or None
    description = (data.get("description") or "").strip() or None
    employment = _employment_type(data.get("employment_type") or data.get("employmentType"))
    posted = data.get("posted_date") or data.get("datePosted")
    loc_block = _parse_location(data.get("location"))
    base_salary = _base_salary(data.get("salary"))
    job: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
    }
    if title:
        job["title"] = title
    if description:
        job["description"] = description
    if posted:
        job["datePosted"] = posted
    if employment:
        job["employmentType"] = employment
    if company:
        job["hiringOrganization"] = {"@type": "Organization", "name": company}
    job.update(loc_block)
    if base_salary:
        job["baseSalary"] = base_salary
    return job
