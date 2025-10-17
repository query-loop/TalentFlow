from __future__ import annotations

import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urljoin


# Site-specific extraction patterns for better accuracy
SITE_PATTERNS = {
    "greenhouse.io": {
        "title": [".app-title", "h1.app-title", "[data-qa='job-name']"],
        "company": [".company-name", "[data-qa='company-name']", "meta[property='og:site_name']"],
        "location": [".location", "[data-qa='job-location']", ".job-location"],
        "description": [".job-post-content", ".section-wrapper--description", "#app-body"],
        "employment_type": [".employment-type", "[data-qa='job-type']"],
    },
    "lever.co": {
        "title": [".posting-headline h2", "h2", ".posting-headline"],
        "company": [".main-header-text a", "meta[property='og:site_name']"],
        "location": [".posting-categories .location", ".sort-by-location"],
        "description": [".posting-content .section-wrapper", ".posting-content"],
    },
    "workday.com": {
        "title": ["[data-automation-id='jobPostingHeader']", "h1"],
        "company": ["[data-automation-id='company']", ".company"],
        "location": ["[data-automation-id='locations']", ".location"],
        "description": ["[data-automation-id='jobPostingDescription']", ".jobDescription"],
    },
    "jobvite.com": {
        "title": [".jv-job-detail-title", "h1"],
        "company": [".jv-job-detail-company", ".company"],
        "location": [".jv-job-detail-location", ".location"],
        "description": [".jv-job-detail-description", ".description"],
    },
    "bamboohr.com": {
        "title": [".BambooHR-ATS-Job-Title", "h1"],
        "company": [".BambooHR-ATS-Company-Name", ".company"],
        "location": [".BambooHR-ATS-Location", ".location"],
        "description": [".BambooHR-ATS-Description", ".description"],
    },
    "smartrecruiters.com": {
        "title": ["[data-test='job-title']", "h1"],
        "company": ["[data-test='company-name']", ".company"],
        "location": ["[data-test='job-location']", ".location"],
        "description": ["[data-test='job-description']", ".description"],
    },
    "linkedin.com": {
        "title": [".top-card-layout__title", "h1"],
        "company": [".topcard__org-name-link", ".topcard__flavor--black-link"],
        "location": [".topcard__flavor--bullet", ".job-criteria__text"],
        "description": [".description__text", ".show-more-less-html__markup"],
    },
    "indeed.com": {
        "title": ["[data-testid='jobsearch-JobInfoHeader-title']", "h1"],
        "company": ["[data-testid='inlineHeader-companyName']", ".icl-u-lg-mr--sm"],
        "location": ["[data-testid='job-location']", ".icl-u-colorForeground--secondary"],
        "description": ["#jobDescriptionText", ".jobsearch-jobDescriptionText"],
    },
    "glassdoor.com": {
        "title": ["[data-test='job-title']", "h2", "h1"],
        "company": ["[data-test='employer-name']", ".employerName"],
        "location": ["[data-test='job-location']", ".location"],
        "description": ["[data-test='jobDescription']", ".jobDescription"],
    },
}


def _format_lever_description_with_links(element, base_url: str) -> str:
    """Format Lever job description converting links to readable text with URLs."""
    try:
        from bs4 import BeautifulSoup, NavigableString
        
        # Clone the element to avoid modifying the original
        desc_clone = element.__copy__()
        
        # Find all links in the description
        links = desc_clone.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Handle relative URLs
            if href.startswith('/') or href.startswith('./'):
                href = urljoin(base_url, href)
            
            # Create readable format: "Link Text (URL)"
            if link_text and href:
                if link_text.lower() != href.lower():
                    readable_link = f"{link_text} ({href})"
                else:
                    readable_link = href
            elif link_text:
                readable_link = link_text
            elif href:
                readable_link = href
            else:
                readable_link = "[Link]"
            
            # Replace the link with readable text
            link.replace_with(readable_link)
        
        # Get the formatted text
        formatted_text = desc_clone.get_text('\n', strip=True)
        
        # Clean up extra whitespace and normalize line breaks
        formatted_text = re.sub(r'\n\s*\n\s*\n', '\n\n', formatted_text)
        formatted_text = re.sub(r' +', ' ', formatted_text)
        
        return formatted_text
        
    except Exception:
        # Fallback to regular text extraction
        return element.get_text(strip=True)


def get_site_key(url: str) -> Optional[str]:
    """Extract site key from URL for pattern matching."""
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower()
        
        # Direct matches
        for site_key in SITE_PATTERNS:
            if site_key in hostname:
                return site_key
        
        # Handle subdomains (e.g., company.greenhouse.io)
        if hostname.endswith(".greenhouse.io"):
            return "greenhouse.io"
        elif hostname.endswith(".lever.co"):
            return "lever.co"
        elif hostname.endswith(".workday.com"):
            return "workday.com"
        elif hostname.endswith(".jobvite.com"):
            return "jobvite.com"
        elif hostname.endswith(".bamboohr.com"):
            return "bamboohr.com"
        elif hostname.endswith(".smartrecruiters.com"):
            return "smartrecruiters.com"
        
        return None
    except Exception:
        return None


def extract_with_site_patterns(url: str, html: str) -> Dict[str, Any]:
    """Extract job data using site-specific CSS selectors."""
    site_key = get_site_key(url)
    if not site_key or site_key not in SITE_PATTERNS:
        return {}
    
    patterns = SITE_PATTERNS[site_key]
    result: Dict[str, Any] = {}
    
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        for field, selectors in patterns.items():
            if field in result and result[field]:  # Skip if already found
                continue
                
            for selector in selectors:
                try:
                    if selector.startswith("meta["):
                        # Handle meta tags specially
                        el = soup.select_one(selector)
                        if el:
                            result[field] = el.get('content', '').strip()
                            break
                    else:
                        el = soup.select_one(selector)
                        if el:
                            # Special handling for description fields with links
                            if field == "description" and site_key == "lever.co":
                                text = _format_lever_description_with_links(el, url)
                            else:
                                text = el.get_text(strip=True)
                            
                            if text and len(text) > 2:
                                result[field] = text
                                break
                except Exception:
                    continue
    
    except ImportError:
        # Fallback to regex if BeautifulSoup not available
        for field, selectors in patterns.items():
            if field in result and result[field]:
                continue
            for selector in selectors:
                try:
                    if "class" in selector or "data-" in selector:
                        # Simple regex for common patterns
                        pattern = rf'<[^>]*{re.escape(selector.replace("[", "").replace("]", ""))}[^>]*>([^<]+)</[^>]*>'
                        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                        if match:
                            result[field] = match.group(1).strip()
                            break
                except Exception:
                    continue
    
    return result


def _format_description_links(description: str, base_url: str) -> str:
    """Convert HTML links in description to readable format with URLs shown."""
    if not description:
        return description
    
    try:
        # Pattern to match HTML links: <a href="url">text</a>
        link_pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>([^<]*)</a>'
        
        def replace_link(match):
            href = match.group(1).strip()
            link_text = match.group(2).strip()
            
            # Handle relative URLs
            if href.startswith('/') or href.startswith('./'):
                href = urljoin(base_url, href)
            
            # Create readable format
            if link_text and href:
                if link_text.lower() != href.lower() and len(link_text) > 0:
                    return f"{link_text} ({href})"
                else:
                    return href
            elif link_text:
                return link_text
            elif href:
                return href
            else:
                return "[Link]"
        
        # Replace all links
        formatted = re.sub(link_pattern, replace_link, description, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up any remaining HTML tags
        formatted = re.sub(r'<[^>]+>', '', formatted)
        
        # Normalize whitespace
        formatted = re.sub(r'\s+', ' ', formatted).strip()
        
        return formatted
        
    except Exception:
        # Fallback: just remove HTML tags
        return re.sub(r'<[^>]+>', '', description).strip()


def enhance_job_data(data: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Post-process extracted data with common sense improvements."""
    enhanced = data.copy()
    
    # Clean and normalize title
    if "title" in enhanced and enhanced["title"]:
        title = str(enhanced["title"])
        # Remove common job board prefixes/suffixes
        title = re.sub(r"^(Job:|Position:|Role:)\s*", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\s*-\s*(Job|Position|Role)$", "", title, flags=re.IGNORECASE)
        enhanced["title"] = title.strip()
    
    # Normalize location
    if "location" in enhanced and enhanced["location"]:
        location = str(enhanced["location"])
        # Clean up common location formats
        location = re.sub(r"^Location:\s*", "", location, flags=re.IGNORECASE)
        location = re.sub(r"\s*\([^)]*\)$", "", location)  # Remove parenthetical info
        enhanced["location"] = location.strip()
    
    # Format description links for better readability
    if "description" in enhanced and enhanced["description"]:
        site_key = get_site_key(url)
        # Skip if already processed by site-specific handler
        if site_key != "lever.co":
            enhanced["description"] = _format_description_links(enhanced["description"], url)
    
    # Extract employment type from description if not found
    if not enhanced.get("employment_type") and enhanced.get("description"):
        desc = str(enhanced["description"]).lower()
        if "full-time" in desc or "full time" in desc:
            enhanced["employment_type"] = "full-time"
        elif "part-time" in desc or "part time" in desc:
            enhanced["employment_type"] = "part-time"
        elif "contract" in desc or "contractor" in desc:
            enhanced["employment_type"] = "contract"
        elif "intern" in desc or "internship" in desc:
            enhanced["employment_type"] = "internship"
    
    # Add source URL
    enhanced["source_url"] = url
    
    return enhanced