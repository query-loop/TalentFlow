from __future__ import annotations

"""
Specialized Lever Job Extractor
Fine-tuned for accurate extraction from all Lever job postings.
"""

import re
from typing import Any, Dict, Optional, List
from urllib.parse import urljoin


class LeverJobExtractor:
    """
    Specialized extractor for Lever job postings with enhanced accuracy
    and comprehensive content extraction.
    """
    
    def __init__(self):
        # Lever-specific CSS selectors based on actual HTML structure analysis
        self.lever_selectors = {
            'title': [
                '.posting-headline h2',
                'h2',
                '[data-qa="job-title"]',
                '.posting-headline .posting-title'
            ],
            'company': [
                '.main-header-logo img@alt',  # Company from logo alt text
                '.main-header-content .main-header-company',
                'meta[property="og:site_name"]@content',
                '.hiringOrganization .name'
            ],
            'location': [
                '.posting-categories .location',
                '.sort-by-time.location',
                '.posting-category.location',
                '[class*="location"]'
            ],
            'department': [
                '.posting-categories .department',
                '.sort-by-team',
                '.posting-category.department'
            ],
            'employment_type': [
                '.posting-categories .commitment',
                '.sort-by-commitment',
                '.posting-category.commitment'
            ],
            'workplace_type': [
                '.posting-categories .workplaceTypes',
                '.posting-category.workplaceTypes'
            ],
            'description': [
                '.section[data-qa="job-description"]',
                '.section.page-centered',
                '.posting-content'
            ],
            'responsibilities': [
                'h3:contains("Core Responsibilities") + div',
                'h3:contains("Responsibilities") + div',
                'h3:contains("What You\'ll Do") + div'
            ],
            'requirements': [
                'h3:contains("What We Require") + div',
                'h3:contains("Requirements") + div',
                'h3:contains("Qualifications") + div'
            ],
            'benefits': [
                'h3:contains("Benefits") + div',
                'h3:contains("What We Offer") + div',
                'h3:contains("Compensation") + div'
            ],
            'values': [
                'h3:contains("What We Value") + div',
                'h3:contains("Our Values") + div'
            ],
            'apply_link': [
                '.postings-btn[href*="apply"]',
                'a[href*="apply"]',
                '.template-btn-submit'
            ],
            'salary': [
                '[data-qa="closing-description"]:contains("salary")',
                'div:contains("$"):contains("year")',
                'div:contains("salary range")'
            ]
        }
        
        # Lever-specific patterns for better extraction
        self.lever_patterns = {
            'salary_range': r'\$(\d{1,3}(?:,\d{3})*)\s*-\s*\$(\d{1,3}(?:,\d{3})*)\s*/?\s*year',
            'email_link': r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            'phone_link': r'tel:([+\d\s()-]+)',
            'company_website': r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.com)',
        }

    def extract_lever_job(self, url: str, html: str) -> Dict[str, Any]:
        """
        Extract comprehensive job data from Lever posting with high accuracy.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return self._fallback_lever_extraction(html, url)
        
        soup = BeautifulSoup(html, 'html.parser')
        result = {}
        
        # Extract JSON-LD structured data first (highest priority)
        json_ld_data = self._extract_lever_json_ld(soup)
        if json_ld_data:
            result.update(json_ld_data)
        
        # Extract basic job information
        result.update(self._extract_lever_basics(soup))
        
        # Extract detailed sections
        result.update(self._extract_lever_sections(soup))
        
        # Extract links and contact information
        result['links'] = self._extract_lever_links(soup, url)
        
        # Extract salary information
        salary_info = self._extract_lever_salary(soup)
        if salary_info:
            result.update(salary_info)
        
        # Clean and enhance the data
        result = self._clean_lever_data(result, url)
        
        return result

    def _extract_lever_json_ld(self, soup) -> Dict[str, Any]:
        """Extract structured data from JSON-LD script tag with robust handling."""
        scripts = soup.find_all('script', type='application/ld+json')
        
        def normalize_location(jl: Any) -> Optional[str]:
            try:
                if isinstance(jl, list) and jl:
                    jl = jl[0]
                if isinstance(jl, dict):
                    addr = jl.get('address') or {}
                    locality = (addr.get('addressLocality') or '').strip()
                    region = (addr.get('addressRegion') or '').strip()
                    country = (addr.get('addressCountry') or '').strip()
                    parts = [p for p in [locality, region, country] if p]
                    if parts:
                        return ', '.join(parts)
                    name = jl.get('name')
                    if name:
                        return str(name).strip()
            except Exception:
                return None
            return None
        
        for script in scripts:
            try:
                import json
                data = json.loads(script.get_text())
            except Exception:
                continue
            
            # Handle direct object, list, or @graph
            items: List[Dict[str, Any]] = []
            if isinstance(data, dict):
                if data.get('@type') == 'JobPosting':
                    items = [data]
                elif isinstance(data.get('@graph'), list):
                    items = [it for it in data['@graph'] if isinstance(it, dict) and it.get('@type') == 'JobPosting']
            elif isinstance(data, list):
                items = [it for it in data if isinstance(it, dict) and it.get('@type') == 'JobPosting']
            
            for item in items:
                result: Dict[str, Any] = {}
                if item.get('title'):
                    result['title'] = str(item['title']).strip()
                
                org = item.get('hiringOrganization') or {}
                if isinstance(org, dict) and org.get('name'):
                    result['company'] = str(org['name']).strip()
                
                loc = normalize_location(item.get('jobLocation'))
                if loc:
                    result['location'] = loc
                
                emp = item.get('employmentType')
                if emp:
                    if isinstance(emp, list):
                        emp = emp[0]
                    result['employment_type'] = str(emp).lower().replace('_', '-').strip()
                
                if item.get('datePosted'):
                    result['date_posted'] = item['datePosted']
                
                if item.get('description'):
                    result['description'] = self._clean_html_description(str(item['description']))
                
                if result:
                    return result
        
        return {}

    def _extract_lever_basics(self, soup) -> Dict[str, Any]:
        """Extract basic job information using CSS selectors."""
        result = {}
        
        # Title
        for selector in self.lever_selectors['title']:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                result['title'] = element.get_text(strip=True)
                break
        
        # Company (from logo alt text or header)
        for selector in self.lever_selectors['company']:
            if '@' in selector:
                sel, attr = selector.split('@')
                element = soup.select_one(sel)
                if element and element.get(attr):
                    # Clean company name from logo alt text
                    company = element.get(attr).replace(' logo', '').replace(' Logo', '').strip()
                    if company and len(company) > 2:
                        result['company'] = company
                        break
            else:
                element = soup.select_one(selector)
                if element and element.get_text(strip=True):
                    result['company'] = element.get_text(strip=True)
                    break
        
        # Location
        for selector in self.lever_selectors['location']:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                location = element.get_text(strip=True)
                # Clean location text
                location = re.sub(r'^(Location:|Loc:)\s*', '', location, flags=re.IGNORECASE)
                if location and len(location) > 2:
                    result['location'] = location
                    break
        
        # Department
        for selector in self.lever_selectors['department']:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                dept = element.get_text(strip=True).rstrip(' /')
                if dept and len(dept) > 1:
                    result['department'] = dept
                    break
        
        # Employment Type
        for selector in self.lever_selectors['employment_type']:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                emp_type = element.get_text(strip=True).rstrip(' /')
                if emp_type and len(emp_type) > 2:
                    result['employment_type'] = emp_type.lower().replace(' ', '-')
                    break
        
        # Workplace Type
        for selector in self.lever_selectors['workplace_type']:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                workplace = element.get_text(strip=True)
                if workplace and len(workplace) > 2:
                    result['workplace_type'] = workplace.lower()
                    break
        
        return result

    def _extract_lever_sections(self, soup) -> Dict[str, Any]:
        """Extract detailed job sections like responsibilities, requirements, etc."""
        result = {}
        
        # Find all section containers
        sections = soup.find_all('div', class_='section page-centered')
        
        for section in sections:
            # Look for h3 headings to identify section types
            heading = section.find('h3')
            if not heading:
                continue
            
            heading_text = heading.get_text(strip=True).lower()
            content_div = heading.find_next_sibling(['div', 'ul'])
            
            if not content_div:
                continue
            
            # Extract list items if present
            list_items = content_div.find_all('li')
            if list_items:
                items = [li.get_text(strip=True) for li in list_items if li.get_text(strip=True)]
                
                if 'responsibilit' in heading_text or 'what you' in heading_text:
                    result['responsibilities'] = items
                elif 'require' in heading_text or 'qualif' in heading_text:
                    result['requirements'] = items
                elif 'benefit' in heading_text or 'what we offer' in heading_text:
                    result['benefits'] = items
                elif 'value' in heading_text or 'what we value' in heading_text:
                    result['values'] = items
            else:
                # Extract plain text content
                content = content_div.get_text(strip=True)
                if content and len(content) > 20:
                    if 'responsibilit' in heading_text:
                        result['responsibilities_text'] = content
                    elif 'require' in heading_text:
                        result['requirements_text'] = content
                    elif 'benefit' in heading_text:
                        result['benefits_text'] = content
        
        return result

    def _extract_lever_salary(self, soup) -> Dict[str, Any]:
        """Extract salary information from the posting."""
        result = {}
        
        # Look for salary in closing description or any div containing salary info
        salary_containers = soup.find_all(['div', 'p'], string=re.compile(r'\$.*year', re.IGNORECASE))
        
        for container in salary_containers:
            text = container.get_text()
            
            # Try to extract salary range
            salary_match = re.search(self.lever_patterns['salary_range'], text, re.IGNORECASE)
            if salary_match:
                min_salary = salary_match.group(1).replace(',', '')
                max_salary = salary_match.group(2).replace(',', '')
                
                result['salary'] = {
                    'min': int(min_salary),
                    'max': int(max_salary),
                    'currency': 'USD',
                    'period': 'yearly',
                    'raw_text': salary_match.group(0)
                }
                break
        
        return result

    def _extract_lever_links(self, soup, base_url: str) -> Dict[str, List[Dict[str, str]]]:
        """Extract and categorize all relevant links from the posting."""
        links = {
            'apply': [],
            'company': [],
            'contact': [],
            'external': []
        }
        
        all_links = soup.find_all('a', href=True)
        seen: set[str] = set()
        
        # Determine company slug from URL path (jobs.lever.co/<slug>/...)
        company_slug = None
        try:
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            parts = [p for p in parsed.path.split('/') if p]
            if parts:
                company_slug = parts[0].lower()
        except Exception:
            company_slug = None
        
        for link in all_links:
            href = (link.get('href') or '').strip()
            text = link.get_text(strip=True)
            
            if not href or href.startswith('#'):
                continue
            
            # Convert relative URLs to absolute
            if href.startswith('/'):
                href = urljoin(base_url, href)
            
            # De-duplicate by URL
            key = href
            if key in seen:
                continue
            seen.add(key)
            
            link_type = self._classify_lever_link(href, text)
            link_data = {'url': href, 'text': text, 'type': link_type}
            
            # Categorize links smartly
            href_lower = href.lower()
            text_lower = (text or '').lower()
            if 'apply' in href_lower or 'apply' in text_lower:
                links['apply'].append(link_data)
            elif href_lower.startswith('mailto:') or href_lower.startswith('tel:'):
                links['contact'].append(link_data)
            elif not href_lower.startswith('https://jobs.lever.co'):
                # Company links: domain contains company slug (if known)
                if company_slug and company_slug in href_lower:
                    links['company'].append(link_data)
                else:
                    links['external'].append(link_data)
        
        return links

    def _classify_lever_link(self, href: str, text: str) -> str:
        """Classify the type of link based on URL and text content."""
        href_lower = href.lower()
        text_lower = text.lower()
        
        if 'apply' in href_lower or 'apply' in text_lower:
            return 'application'
        elif 'mailto:' in href:
            return 'email'
        elif 'tel:' in href:
            return 'phone'
        elif any(word in text_lower for word in ['career', 'life at', 'culture', 'about']):
            return 'company_info'
        elif any(word in text_lower for word in ['benefit', 'compensation', 'package']):
            return 'benefits'
        else:
            return 'general'

    def _clean_html_description(self, html_desc: str) -> str:
        """Clean HTML description while preserving structure."""
        if not html_desc:
            return ""
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_desc, 'html.parser')
            
            # Convert links to readable format
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                text = link.get_text(strip=True)
                
                if text and href and text.lower() != href.lower():
                    link.replace_with(f"{text} ({href})")
                elif href:
                    link.replace_with(href)
                elif text:
                    link.replace_with(text)
            
            # Convert to text with proper formatting
            text = soup.get_text('\n', strip=True)
            
            # Normalize unicode whitespace
            text = re.sub(r'[\u00A0\u2000-\u200B\u202F\u205F\u3000]', ' ', text)
            # Clean up extra whitespace
            text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
            text = re.sub(r' +', ' ', text)
            
            return text.strip()
            
        except Exception:
            # Fallback: strip HTML tags
            return re.sub(r'<[^>]+>', '', html_desc).strip()

    def _clean_lever_data(self, data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Clean and enhance extracted data."""
        cleaned = data.copy()
        
        # Add metadata
        cleaned['source_url'] = url
        cleaned['source_platform'] = 'lever'
        cleaned['extraction_method'] = 'lever_specialized'
        
        # Clean title
        if 'title' in cleaned and cleaned['title']:
            title = str(cleaned['title'])
            # Remove common Lever artifacts
            title = re.sub(r'^(Job:|Position:|Role:)\s*', '', title, flags=re.IGNORECASE)
            cleaned['title'] = title.strip()
        
        # Combine description sections if needed
        if not cleaned.get('description') and any(key in cleaned for key in ['responsibilities_text', 'requirements_text']):
            desc_parts = []
            if cleaned.get('responsibilities_text'):
                desc_parts.append(f"**Responsibilities:**\n{cleaned['responsibilities_text']}")
            if cleaned.get('requirements_text'):
                desc_parts.append(f"**Requirements:**\n{cleaned['requirements_text']}")
            if cleaned.get('benefits_text'):
                desc_parts.append(f"**Benefits:**\n{cleaned['benefits_text']}")
            
            cleaned['description'] = '\n\n'.join(desc_parts)
        
        # Add confidence score based on data completeness
        confidence_factors = [
            bool(cleaned.get('title')),
            bool(cleaned.get('company')),
            bool(cleaned.get('location')),
            bool(cleaned.get('description')),
            bool(cleaned.get('employment_type')),
            bool(cleaned.get('requirements') or cleaned.get('requirements_text')),
        ]
        
        cleaned['confidence_score'] = sum(confidence_factors) / len(confidence_factors)
        
        return cleaned

    def _fallback_lever_extraction(self, html: str, url: str) -> Dict[str, Any]:
        """Fallback extraction when BeautifulSoup is not available."""
        result = {
            'source_url': url,
            'source_platform': 'lever',
            'extraction_method': 'lever_regex_fallback',
            'confidence_score': 0.3
        }
        
        # Basic regex extraction
        title_match = re.search(r'<h2[^>]*>([^<]+)</h2>', html, re.IGNORECASE)
        if title_match:
            result['title'] = title_match.group(1).strip()
        
        # Extract company from JSON-LD
        json_ld_match = re.search(r'"hiringOrganization"[^}]*"name"\s*:\s*"([^"]+)"', html)
        if json_ld_match:
            result['company'] = json_ld_match.group(1).strip()
        
        return result