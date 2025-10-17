"""
Advanced job parsing with support for multiple ATS platforms and JSON-LD.
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import json
import re
import logging

logger = logging.getLogger(__name__)

def _clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Replace common whitespace issues
    text = re.sub(r'\r', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    
    return text

def _extract_text_safe(element) -> str:
    """Safely extract text from BeautifulSoup element"""
    if not element:
        return ""
    try:
        return _clean_text(element.get_text(' ', strip=True))
    except Exception:
        return ""

def parse_job_from_html(url: str, html: str) -> Dict[str, Any]:
    """
    Parse job information from HTML using multiple strategies:
    1. JSON-LD structured data
    2. ATS-specific selectors
    3. Generic fallback parsing
    """
    if not html:
        return {"title": "Job", "company": None, "location": None, "description": "", "source_url": url}
    
    soup = BeautifulSoup(html, 'lxml')
    
    # Strategy 1: JSON-LD JobPosting
    job_data = _parse_jsonld_jobposting(soup, url)
    if job_data and job_data.get("description"):
        logger.info(f"Successfully parsed {url} using JSON-LD")
        return job_data
    
    # Strategy 2: ATS-specific parsing
    ats_parsers = [
        _parse_lever,
        _parse_greenhouse,
        _parse_workday,
        _parse_bamboohr,
        _parse_smartrecruiters,
        _parse_ashbyhq,
        _parse_jobvite,
    ]
    
    for parser in ats_parsers:
        try:
            job_data = parser(url, soup)
            if job_data and job_data.get("description"):
                logger.info(f"Successfully parsed {url} using {parser.__name__}")
                return job_data
        except Exception as e:
            logger.warning(f"Parser {parser.__name__} failed for {url}: {e}")
            continue
    
    # Strategy 3: Generic fallback
    job_data = _parse_generic(url, soup)
    logger.info(f"Parsed {url} using generic fallback")
    return job_data

def _parse_jsonld_jobposting(soup: BeautifulSoup, url: str) -> Optional[Dict[str, Any]]:
    """Parse JSON-LD JobPosting structured data"""
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or "{}")
            
            # Handle both single objects and arrays
            items = data if isinstance(data, list) else [data]
            
            for item in items:
                if item.get("@type") == "JobPosting":
                    return _extract_from_jobposting(item, url)
                
                # Sometimes nested in other structures
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, dict) and value.get("@type") == "JobPosting":
                            return _extract_from_jobposting(value, url)
                        elif isinstance(value, list):
                            for subitem in value:
                                if isinstance(subitem, dict) and subitem.get("@type") == "JobPosting":
                                    return _extract_from_jobposting(subitem, url)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Failed to parse JSON-LD: {e}")
            continue
    
    return None

def _extract_from_jobposting(data: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Extract job data from JobPosting structured data"""
    # Extract title
    title = data.get("title") or "Job"
    
    # Extract company
    company = None
    org = data.get("hiringOrganization")
    if isinstance(org, dict):
        company = org.get("name")
    elif isinstance(org, str):
        company = org
    
    # Extract location
    location = None
    job_location = data.get("jobLocation")
    if isinstance(job_location, list) and job_location:
        loc_data = job_location[0]
    elif isinstance(job_location, dict):
        loc_data = job_location
    else:
        loc_data = {}
    
    if isinstance(loc_data, dict):
        address = loc_data.get("address", {})
        if isinstance(address, dict):
            location_parts = []
            for field in ["addressLocality", "addressRegion", "addressCountry"]:
                if address.get(field):
                    location_parts.append(address[field])
            location = ", ".join(location_parts) if location_parts else None
        elif isinstance(address, str):
            location = address
    
    # Extract description
    description = data.get("description", "")
    if description:
        # Clean HTML from description
        desc_soup = BeautifulSoup(description, 'lxml')
        description = _clean_text(desc_soup.get_text('\n'))
    
    # Extract additional fields
    employment_type = data.get("employmentType")
    date_posted = data.get("datePosted")
    salary = None
    
    base_salary = data.get("baseSalary")
    if isinstance(base_salary, dict):
        value = base_salary.get("value", {})
        if isinstance(value, dict):
            min_val = value.get("minValue")
            max_val = value.get("maxValue")
            currency = base_salary.get("currency", "USD")
            
            if min_val and max_val:
                salary = f"{currency} {min_val}-{max_val}"
            elif min_val:
                salary = f"{currency} {min_val}+"
    
    return {
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "employment_type": employment_type,
        "date_posted": date_posted,
        "salary": salary,
        "source_url": url,
    }

def _parse_lever(url: str, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Parse Lever job pages"""
    if "jobs.lever.co" not in url and "lever.co" not in url:
        return None
    
    title = soup.find("h2", class_="posting-headline") or soup.find("h1") or soup.find("h2")
    company = soup.find("a", {"data-qa": "company-name"}) or soup.select_one(".posting-headline .company")
    location = soup.select_one(".location") or soup.select_one(".posting-headline .location")
    
    # Description can be in multiple containers
    desc = (soup.select_one(".section-wrapper") or 
           soup.select_one(".content") or 
           soup.select_one(".posting-requirements") or
           soup.select_one(".posting-description"))
    
    return {
        "title": _extract_text_safe(title) or "Job",
        "company": _extract_text_safe(company),
        "location": _extract_text_safe(location),
        "description": _extract_text_safe(desc),
        "source_url": url,
    }

def _parse_greenhouse(url: str, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Parse Greenhouse job pages"""
    if "boards.greenhouse.io" not in url and "greenhouse.io" not in url:
        return None
    
    title = soup.select_one("h1.app-title") or soup.find("h1")
    company = soup.select_one(".company-name") or soup.select_one(".header-company-name")
    location = soup.select_one(".location")
    
    desc = (soup.select_one("#content") or 
           soup.select_one(".content") or 
           soup.select_one(".opening"))
    
    return {
        "title": _extract_text_safe(title) or "Job",
        "company": _extract_text_safe(company),
        "location": _extract_text_safe(location),
        "description": _extract_text_safe(desc),
        "source_url": url,
    }

def _parse_workday(url: str, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Parse Workday job pages"""
    if ".myworkdayjobs.com" not in url and "workday" not in url:
        return None
    
    title = soup.find("h1")
    company = soup.select_one("[data-automation-id='company']") or soup.select_one(".company")
    location = soup.select_one("[data-automation-id='locations']") or soup.select_one(".location")
    
    desc = (soup.select_one("[data-automation-id='jobPostingDescription']") or
           soup.select_one(".jobPostingDescription") or
           soup.select_one("#jobDescription"))
    
    return {
        "title": _extract_text_safe(title) or "Job",
        "company": _extract_text_safe(company),
        "location": _extract_text_safe(location),
        "description": _extract_text_safe(desc),
        "source_url": url,
    }

def _parse_bamboohr(url: str, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Parse BambooHR job pages"""
    if "bamboohr.com" not in url:
        return None
    
    title = soup.find("h1") or soup.select_one(".job-title")
    company = soup.select_one(".company-name") or soup.select_one(".employer-name")
    location = soup.select_one(".job-location") or soup.select_one(".location")
    desc = soup.select_one(".job-description") or soup.select_one(".description")
    
    return {
        "title": _extract_text_safe(title) or "Job",
        "company": _extract_text_safe(company),
        "location": _extract_text_safe(location),
        "description": _extract_text_safe(desc),
        "source_url": url,
    }

def _parse_smartrecruiters(url: str, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Parse SmartRecruiters job pages"""
    if "smartrecruiters.com" not in url:
        return None
    
    title = soup.select_one("h1.details-header__job-title") or soup.find("h1")
    company = soup.select_one(".details-header__company-name") or soup.select_one(".company-name")
    location = soup.select_one(".details-header__job-location") or soup.select_one(".job-location")
    desc = soup.select_one(".details__description") or soup.select_one(".job-description")
    
    return {
        "title": _extract_text_safe(title) or "Job",
        "company": _extract_text_safe(company),
        "location": _extract_text_safe(location),
        "description": _extract_text_safe(desc),
        "source_url": url,
    }

def _parse_ashbyhq(url: str, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Parse Ashby job pages"""
    if "ashbyhq.com" not in url and "jobs.ashbyhq.com" not in url:
        return None
    
    title = soup.find("h1") or soup.select_one(".job__title")
    company = soup.select_one(".job__company") or soup.select_one(".company")
    location = soup.select_one(".job__location") or soup.select_one(".location")
    desc = soup.select_one(".job__description") or soup.select_one(".description")
    
    return {
        "title": _extract_text_safe(title) or "Job",
        "company": _extract_text_safe(company),
        "location": _extract_text_safe(location),
        "description": _extract_text_safe(desc),
        "source_url": url,
    }

def _parse_jobvite(url: str, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Parse Jobvite job pages"""
    if "jobvite.com" not in url:
        return None
    
    title = soup.select_one(".jv-job-detail-title") or soup.find("h1")
    company = soup.select_one(".jv-job-detail-company") or soup.select_one(".company")
    location = soup.select_one(".jv-job-detail-location") or soup.select_one(".location")
    desc = soup.select_one(".jv-job-detail-description") or soup.select_one(".description")
    
    return {
        "title": _extract_text_safe(title) or "Job",
        "company": _extract_text_safe(company),
        "location": _extract_text_safe(location),
        "description": _extract_text_safe(desc),
        "source_url": url,
    }

def _parse_generic(url: str, soup: BeautifulSoup) -> Dict[str, Any]:
    """Generic fallback parser for job pages"""
    # Try common selectors for title
    title_selectors = [
        "h1", "h2", ".job-title", ".title", ".posting-headline",
        "[class*='title']", "[id*='title']"
    ]
    
    title = None
    for selector in title_selectors:
        element = soup.select_one(selector)
        if element:
            title = _extract_text_safe(element)
            if title and len(title) > 3:
                break
    
    # Try common selectors for company
    company_selectors = [
        ".company", ".company-name", ".employer", "[data-company]",
        "[class*='company']", "[class*='employer']"
    ]
    
    company = None
    for selector in company_selectors:
        element = soup.select_one(selector)
        if element:
            company = _extract_text_safe(element)
            if company and len(company) > 1:
                break
    
    # Try common selectors for location
    location_selectors = [
        ".location", ".job-location", "[data-location]",
        "[class*='location']", "[id*='location']"
    ]
    
    location = None
    for selector in location_selectors:
        element = soup.select_one(selector)
        if element:
            location = _extract_text_safe(element)
            if location and len(location) > 1:
                break
    
    # Try common selectors for description
    desc_selectors = [
        ".description", ".job-description", ".content", ".job-content",
        ".posting-description", "#job-description", "article", "main",
        "[class*='description']", "[id*='description']"
    ]
    
    description = ""
    for selector in desc_selectors:
        element = soup.select_one(selector)
        if element:
            description = _extract_text_safe(element)
            if description and len(description) > 100:
                break
    
    # Fallback to body text if no good description found
    if not description or len(description) < 50:
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        description = _clean_text(soup.get_text('\n'))
    
    return {
        "title": title or "Job",
        "company": company,
        "location": location,
        "description": description,
        "source_url": url,
    }