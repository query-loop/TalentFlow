#!/usr/bin/env python3
"""
Production-ready job posting scraper with headless rendering, multi-method extraction,
schema validation, and provenance tracking.
"""

import asyncio
import json
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse
from pathlib import Path

import jsonschema
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SalaryInfo:
    min: Optional[float] = None
    max: Optional[float] = None
    currency: str = "USD"
    period: str = "yearly"

@dataclass
class ProvenanceInfo:
    extraction_method: str
    confidence_score: float
    field_sources: Dict[str, str]
    warnings: List[str]

@dataclass
class JobPosting:
    title: str
    company: str
    source_url: str
    retrieved_at: str
    req_id: Optional[str] = None
    team: Optional[str] = None
    level: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    posted_date: Optional[str] = None
    description: str = ""
    responsibilities: List[str] = None
    qualifications: List[str] = None
    skills: List[str] = None
    salary: Optional[SalaryInfo] = None
    benefits: List[str] = None
    apply_url: Optional[str] = None
    provenance: Optional[ProvenanceInfo] = None

    def __post_init__(self):
        if self.responsibilities is None:
            self.responsibilities = []
        if self.qualifications is None:
            self.qualifications = []
        if self.skills is None:
            self.skills = []
        if self.benefits is None:
            self.benefits = []

class JobScraper:
    """Production job posting scraper with multiple extraction strategies"""
    
    def __init__(self, schema_path: Optional[str] = None):
        self.schema_path = schema_path or str(Path(__file__).parent.parent / "contracts" / "schemas" / "job_scraper.json")
        self.schema = self._load_schema()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # Common skill patterns for extraction
        self.skill_patterns = [
            r'\b(?:JavaScript|TypeScript|Python|Java|C\+\+|C#|Go|Rust|PHP|Ruby|Swift|Kotlin)\b',
            r'\b(?:React|Vue|Angular|Svelte|Node\.js|Express|Django|Flask|FastAPI|Spring)\b',
            r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|Git|PostgreSQL|MySQL|MongoDB)\b',
            r'\b(?:HTML|CSS|SQL|REST|GraphQL|API|CI/CD|DevOps|Agile|Scrum)\b'
        ]
        
        # Employment type normalization
        self.employment_type_map = {
            'full time': 'full-time',
            'fulltime': 'full-time',
            'part time': 'part-time',
            'parttime': 'part-time',
            'contractor': 'contract',
            'consulting': 'contract',
            'intern': 'internship',
            'temporary': 'temporary',
            'freelance': 'freelance'
        }
        
        # Level normalization
        self.level_patterns = {
            'intern': r'\b(?:intern|internship)\b',
            'entry': r'\b(?:entry|graduate|junior|jr\.?|associate)\b',
            'junior': r'\b(?:junior|jr\.?)\b',
            'mid': r'\b(?:mid|intermediate|ii|2)\b',
            'senior': r'\b(?:senior|sr\.?|iii|3)\b',
            'staff': r'\b(?:staff)\b',
            'principal': r'\b(?:principal)\b',
            'lead': r'\b(?:lead|tech lead|technical lead)\b',
            'manager': r'\b(?:manager|mgr|engineering manager)\b',
            'director': r'\b(?:director|head of)\b',
            'vp': r'\b(?:vp|vice president)\b',
            'c-level': r'\b(?:cto|ceo|cfo|coo|chief)\b'
        }

    def _load_schema(self) -> Dict[str, Any]:
        """Load and parse JSON schema"""
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Schema file not found: {self.schema_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON schema: {e}")
            return {}

    @asynccontextmanager
    async def browser_session(self):
        """Async context manager for browser lifecycle"""
        playwright = await async_playwright().start()
        try:
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',  # Faster loading
                    '--disable-javascript-harmony-shipping',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            yield self.context
        finally:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            await playwright.stop()

    async def scrape_job(self, url: str, max_retries: int = 3) -> JobPosting:
        """Main scraping method with retry logic"""
        for attempt in range(max_retries + 1):
            try:
                async with self.browser_session() as context:
                    page = await context.new_page()
                    
                    # Navigate with robust waiting
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    
                    # Wait for potential dynamic content
                    await page.wait_for_timeout(2000)
                    
                    # Try to wait for common job posting indicators
                    try:
                        await page.wait_for_selector(
                            'script[type="application/ld+json"], .job-description, .posting, article, main',
                            timeout=5000
                        )
                    except:
                        pass  # Continue even if no specific selectors found
                    
                    # Extract data using multiple methods
                    job_data = await self._extract_job_data(page, url)
                    
                    # Validate and repair
                    validated_job = self._validate_and_repair(job_data)
                    
                    return validated_job
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries:
                    raise Exception(f"Failed to scrape job after {max_retries + 1} attempts: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def _extract_job_data(self, page: Page, url: str) -> Dict[str, Any]:
        """Extract job data using multiple methods with provenance tracking"""
        extraction_methods = []
        field_sources = {}
        warnings = []
        confidence_scores = []
        
        # Method 1: JSON-LD structured data
        json_ld_data = await self._extract_json_ld(page)
        if json_ld_data:
            extraction_methods.append('json-ld')
            confidence_scores.append(0.9)
            logger.info("Found JSON-LD structured data")
        
        # Method 2: Microdata
        microdata = await self._extract_microdata(page)
        if microdata:
            extraction_methods.append('microdata')
            confidence_scores.append(0.8)
            logger.info("Found microdata")
        
        # Method 3: DOM selectors
        dom_data = await self._extract_dom_selectors(page)
        extraction_methods.append('dom-selectors')
        confidence_scores.append(0.6)
        
        # Method 4: Regex fallbacks on page text
        page_text = await page.text_content('body')
        regex_data = self._extract_regex_fallbacks(page_text or "")
        
        # Merge data with priority: JSON-LD > Microdata > DOM > Regex
        merged_data = self._merge_extraction_data(
            json_ld_data, microdata, dom_data, regex_data, field_sources
        )
        
        # Add metadata
        merged_data.update({
            'source_url': url,
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'provenance': {
                'extraction_method': extraction_methods[0] if extraction_methods else 'dom-selectors',
                'confidence_score': max(confidence_scores) if confidence_scores else 0.5,
                'field_sources': field_sources,
                'warnings': warnings
            }
        })
        
        return merged_data

    async def _extract_json_ld(self, page: Page) -> Dict[str, Any]:
        """Extract JobPosting from JSON-LD structured data"""
        try:
            scripts = await page.query_selector_all('script[type="application/ld+json"]')
            
            for script in scripts:
                try:
                    content = await script.text_content()
                    if not content:
                        continue
                        
                    data = json.loads(content)
                    
                    # Handle both single objects and arrays
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        if item.get('@type') == 'JobPosting':
                            return self._parse_json_ld_job_posting(item)
                            
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.debug(f"JSON-LD extraction failed: {e}")
            
        return {}

    def _parse_json_ld_job_posting(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JobPosting from JSON-LD data"""
        result = {}
        
        # Basic fields
        if 'title' in data:
            result['title'] = str(data['title']).strip()
        
        # Hiring organization
        org = data.get('hiringOrganization', {})
        if isinstance(org, dict) and 'name' in org:
            result['company'] = str(org['name']).strip()
        elif isinstance(org, str):
            result['company'] = org.strip()
        
        # Location
        location = data.get('jobLocation', {})
        if isinstance(location, list) and location:
            location = location[0]
        if isinstance(location, dict):
            address = location.get('address', {})
            if isinstance(address, dict):
                loc_parts = []
                for key in ['addressLocality', 'addressRegion', 'addressCountry']:
                    if key in address and address[key]:
                        loc_parts.append(str(address[key]))
                if loc_parts:
                    result['location'] = ', '.join(loc_parts)
            elif location.get('name'):
                result['location'] = str(location['name'])
        
        # Employment type
        emp_type = data.get('employmentType')
        if emp_type:
            result['employment_type'] = self._normalize_employment_type(str(emp_type))
        
        # Posted date
        posted = data.get('datePosted')
        if posted:
            result['posted_date'] = self._normalize_date(str(posted))
        
        # Description
        if 'description' in data:
            result['description'] = str(data['description']).strip()
        
        # Salary
        salary = data.get('baseSalary', {})
        if isinstance(salary, dict):
            value = salary.get('value', {})
            if isinstance(value, dict):
                salary_info = {}
                if 'minValue' in value:
                    salary_info['min'] = float(value['minValue'])
                if 'maxValue' in value:
                    salary_info['max'] = float(value['maxValue'])
                if 'currency' in value:
                    salary_info['currency'] = str(value['currency'])
                if salary_info:
                    result['salary'] = salary_info
        
        # Qualifications and responsibilities
        qualifications = data.get('qualifications', [])
        if isinstance(qualifications, list):
            result['qualifications'] = [str(q).strip() for q in qualifications if q]
        
        responsibilities = data.get('responsibilities', [])
        if isinstance(responsibilities, list):
            result['responsibilities'] = [str(r).strip() for r in responsibilities if r]
        
        # Apply URL
        apply_url = data.get('url') or data.get('applicationContact', {}).get('url')
        if apply_url:
            result['apply_url'] = str(apply_url)
        
        return result

    async def _extract_microdata(self, page: Page) -> Dict[str, Any]:
        """Extract job data from microdata attributes"""
        try:
            # Look for itemtype="http://schema.org/JobPosting"
            job_elements = await page.query_selector_all('[itemtype*="JobPosting"]')
            
            if not job_elements:
                return {}
            
            result = {}
            job_element = job_elements[0]  # Use first found
            
            # Extract microdata properties
            properties = await page.query_selector_all('[itemprop]')
            
            for prop in properties:
                try:
                    prop_name = await prop.get_attribute('itemprop')
                    if not prop_name:
                        continue
                    
                    # Get content or text
                    content = await prop.get_attribute('content')
                    if not content:
                        content = await prop.text_content()
                    
                    if not content:
                        continue
                    
                    content = content.strip()
                    
                    # Map microdata properties to our schema
                    if prop_name == 'title':
                        result['title'] = content
                    elif prop_name == 'hiringOrganization':
                        result['company'] = content
                    elif prop_name == 'jobLocation':
                        result['location'] = content
                    elif prop_name == 'employmentType':
                        result['employment_type'] = self._normalize_employment_type(content)
                    elif prop_name == 'datePosted':
                        result['posted_date'] = self._normalize_date(content)
                    elif prop_name == 'description':
                        result['description'] = content
                    elif prop_name == 'url':
                        result['apply_url'] = content
                        
                except Exception:
                    continue
            
            return result
            
        except Exception as e:
            logger.debug(f"Microdata extraction failed: {e}")
            return {}

    async def _extract_dom_selectors(self, page: Page) -> Dict[str, Any]:
        """Extract job data using common DOM selectors"""
        result = {}
        
        # Title selectors
        title_selectors = [
            'h1[class*="job"]', 'h1[class*="title"]', 'h1[class*="position"]',
            '.job-title', '.position-title', '.posting-title',
            'h1', 'h2[class*="job"]', '[data-testid*="job-title"]'
        ]
        
        for selector in title_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and len(text.strip()) > 0:
                        result['title'] = text.strip()
                        break
            except:
                continue
        
        # Company selectors
        company_selectors = [
            '.company-name', '.employer-name', '[class*="company"]',
            '[data-testid*="company"]', '.hiring-company',
            'a[href*="company"]', '.org-name'
        ]
        
        for selector in company_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and len(text.strip()) > 0:
                        result['company'] = text.strip()
                        break
            except:
                continue
        
        # Location selectors
        location_selectors = [
            '.job-location', '.location', '[class*="location"]',
            '[data-testid*="location"]', '.work-location'
        ]
        
        for selector in location_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and len(text.strip()) > 0:
                        result['location'] = text.strip()
                        break
            except:
                continue
        
        # Description selectors
        desc_selectors = [
            '.job-description', '.posting-description', '.description',
            '[class*="job-desc"]', '.job-details', '.position-description',
            'main', 'article', '.content'
        ]
        
        for selector in desc_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and len(text.strip()) > 50:  # Minimum length
                        result['description'] = text.strip()
                        break
            except:
                continue
        
        # Employment type from common patterns
        page_text = await page.text_content('body') or ""
        emp_type = self._extract_employment_type(page_text)
        if emp_type:
            result['employment_type'] = emp_type
        
        # Extract level from title and text
        level = self._extract_level(result.get('title', '') + ' ' + page_text[:1000])
        if level:
            result['level'] = level
        
        # Extract lists (responsibilities, qualifications)
        lists = await self._extract_lists_from_dom(page)
        result.update(lists)
        
        return result

    async def _extract_lists_from_dom(self, page: Page) -> Dict[str, List[str]]:
        """Extract lists of responsibilities, qualifications, etc."""
        result = {'responsibilities': [], 'qualifications': [], 'benefits': []}
        
        # Look for list sections
        list_sections = await page.query_selector_all('ul, ol')
        
        for section in list_sections:
            try:
                # Get context text around the list
                parent = await section.query_selector('..')
                if parent:
                    context_text = await parent.text_content()
                else:
                    context_text = ""
                
                context_text = (context_text or "").lower()
                
                # Get list items
                items = await section.query_selector_all('li')
                list_items = []
                
                for item in items:
                    text = await item.text_content()
                    if text and len(text.strip()) > 5:
                        list_items.append(text.strip())
                
                if not list_items:
                    continue
                
                # Categorize based on context
                if any(word in context_text for word in ['responsibilit', 'duties', 'role', 'you will']):
                    result['responsibilities'].extend(list_items[:20])  # Limit items
                elif any(word in context_text for word in ['qualifi', 'requirement', 'skill', 'experience']):
                    result['qualifications'].extend(list_items[:20])
                elif any(word in context_text for word in ['benefit', 'perk', 'offer']):
                    result['benefits'].extend(list_items[:15])
                    
            except:
                continue
        
        # Remove duplicates and clean
        for key in result:
            result[key] = list(dict.fromkeys(result[key]))  # Remove duplicates
            result[key] = [item for item in result[key] if len(item) >= 5]  # Min length
        
        return result

    def _extract_regex_fallbacks(self, text: str) -> Dict[str, Any]:
        """Extract data using regex patterns as fallback"""
        result = {}
        
        if not text:
            return result
        
        # Extract skills using patterns
        skills = set()
        for pattern in self.skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.update(match.strip() for match in matches)
        
        if skills:
            result['skills'] = list(skills)[:50]  # Limit skills
        
        # Extract salary information
        salary_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K|thousand)?\s*(?:-|to)\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K|thousand)?\s*(?:per\s+)?(year|annual|hour|month)?'
        salary_match = re.search(salary_pattern, text, re.IGNORECASE)
        
        if salary_match:
            try:
                min_sal = float(salary_match.group(1).replace(',', ''))
                max_sal = float(salary_match.group(2).replace(',', ''))
                period = salary_match.group(3) or 'yearly'
                
                # Convert K notation
                if 'k' in salary_match.group(0).lower():
                    min_sal *= 1000
                    max_sal *= 1000
                
                result['salary'] = {
                    'min': min_sal,
                    'max': max_sal,
                    'currency': 'USD',
                    'period': 'yearly' if period.lower() in ['year', 'annual'] else 'hourly'
                }
            except:
                pass
        
        return result

    def _merge_extraction_data(self, json_ld: Dict, microdata: Dict, dom: Dict, 
                             regex: Dict, field_sources: Dict) -> Dict[str, Any]:
        """Merge data from different extraction methods with priority"""
        result = {}
        
        # Priority order: JSON-LD > Microdata > DOM > Regex
        sources = [
            (json_ld, 'json-ld'),
            (microdata, 'microdata'),
            (dom, 'dom'),
            (regex, 'regex')
        ]
        
        # Define all possible fields
        all_fields = [
            'title', 'company', 'req_id', 'team', 'level', 'location',
            'employment_type', 'posted_date', 'description', 'responsibilities',
            'qualifications', 'skills', 'salary', 'benefits', 'apply_url'
        ]
        
        for field in all_fields:
            for data, source_name in sources:
                if field in data and data[field]:
                    # For lists, merge unique items
                    if field in ['responsibilities', 'qualifications', 'skills', 'benefits']:
                        if field not in result:
                            result[field] = []
                        if isinstance(data[field], list):
                            # Add unique items
                            for item in data[field]:
                                if item not in result[field]:
                                    result[field].append(item)
                        field_sources[field] = field_sources.get(field, source_name)
                    else:
                        # For single values, use first found (highest priority)
                        if field not in result:
                            result[field] = data[field]
                            field_sources[field] = source_name
        
        return result

    def _normalize_employment_type(self, emp_type: str) -> Optional[str]:
        """Normalize employment type to schema enum"""
        if not emp_type:
            return None
        
        emp_type = emp_type.lower().strip()
        
        return self.employment_type_map.get(emp_type, emp_type if emp_type in [
            'full-time', 'part-time', 'contract', 'temporary', 'internship', 'freelance'
        ] else None)

    def _extract_employment_type(self, text: str) -> Optional[str]:
        """Extract employment type from text"""
        text_lower = text.lower()
        
        for normalized, pattern in [
            ('full-time', r'\b(?:full[- ]?time|fulltime)\b'),
            ('part-time', r'\b(?:part[- ]?time|parttime)\b'),
            ('contract', r'\b(?:contract|contractor|consulting)\b'),
            ('internship', r'\b(?:intern|internship)\b'),
            ('temporary', r'\b(?:temporary|temp)\b'),
            ('freelance', r'\b(?:freelance|freelancer)\b')
        ]:
            if re.search(pattern, text_lower):
                return normalized
        
        return None

    def _extract_level(self, text: str) -> Optional[str]:
        """Extract seniority level from text"""
        text_lower = text.lower()
        
        # Check patterns in reverse order of seniority for priority
        for level, pattern in reversed(list(self.level_patterns.items())):
            if re.search(pattern, text_lower):
                return level
        
        return None

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date string to ISO format"""
        if not date_str:
            return None
        
        try:
            # Handle common formats
            from dateutil import parser
            parsed_date = parser.parse(date_str)
            return parsed_date.date().isoformat()
        except:
            return None

    def _validate_and_repair(self, data: Dict[str, Any]) -> JobPosting:
        """Validate data against schema and attempt repairs"""
        warnings = data.get('provenance', {}).get('warnings', [])
        
        # Required field validation and repair
        if not data.get('title'):
            if data.get('description'):
                # Try to extract title from first line of description
                first_line = data['description'].split('\n')[0].strip()
                if len(first_line) < 100:  # Reasonable title length
                    data['title'] = first_line
                    warnings.append("Title extracted from description first line")
                else:
                    data['title'] = "Job Opening"
                    warnings.append("Title missing, used default")
            else:
                data['title'] = "Job Opening"
                warnings.append("Title missing, used default")
        
        if not data.get('company'):
            # Try to extract from URL
            try:
                from urllib.parse import urlparse
                parsed = urlparse(data.get('source_url', ''))
                hostname = parsed.hostname or ''
                if hostname:
                    # Remove common prefixes
                    hostname = re.sub(r'^(www\.|jobs\.|careers\.)', '', hostname)
                    # Take first part before TLD
                    company_guess = hostname.split('.')[0].title()
                    if company_guess and len(company_guess) > 2:
                        data['company'] = company_guess
                        warnings.append(f"Company name guessed from URL: {company_guess}")
                    else:
                        data['company'] = "Unknown Company"
                        warnings.append("Company name missing, used default")
                else:
                    data['company'] = "Unknown Company"
                    warnings.append("Company name missing, used default")
            except:
                data['company'] = "Unknown Company"
                warnings.append("Company name missing, used default")
        
        # Ensure description has minimum content
        if not data.get('description') or len(data['description']) < 50:
            if data.get('responsibilities') or data.get('qualifications'):
                desc_parts = []
                if data.get('responsibilities'):
                    desc_parts.append("Responsibilities:\n" + "\n".join(f"• {r}" for r in data['responsibilities'][:10]))
                if data.get('qualifications'):
                    desc_parts.append("Qualifications:\n" + "\n".join(f"• {q}" for q in data['qualifications'][:10]))
                data['description'] = "\n\n".join(desc_parts)
                warnings.append("Description generated from extracted lists")
            else:
                data['description'] = f"Job opening at {data.get('company', 'Company')} for {data.get('title', 'Position')}"
                warnings.append("Description missing, used minimal default")
        
        # Update warnings
        if 'provenance' in data:
            data['provenance']['warnings'] = warnings
        
        # Convert to JobPosting object
        try:
            # Handle nested objects
            salary_data = data.get('salary')
            if salary_data and isinstance(salary_data, dict):
                salary = SalaryInfo(**salary_data)
            else:
                salary = None
            
            provenance_data = data.get('provenance', {})
            provenance = ProvenanceInfo(**provenance_data) if provenance_data else None
            
            # Create JobPosting
            job_data = {k: v for k, v in data.items() if k not in ['salary', 'provenance']}
            job = JobPosting(**job_data, salary=salary, provenance=provenance)
            
            # Validate against JSON schema if available
            if self.schema:
                try:
                    # Convert to dict for validation
                    job_dict = asdict(job)
                    # Handle nested dataclasses
                    if job_dict.get('salary'):
                        job_dict['salary'] = asdict(job.salary) if job.salary else None
                    if job_dict.get('provenance'):
                        job_dict['provenance'] = asdict(job.provenance) if job.provenance else None
                    
                    jsonschema.validate(job_dict, self.schema)
                    logger.info("Data validated against schema successfully")
                    
                except jsonschema.ValidationError as e:
                    logger.warning(f"Schema validation failed: {e.message}")
                    if job.provenance:
                        job.provenance.warnings.append(f"Schema validation warning: {e.message}")
                    
            return job
            
        except Exception as e:
            logger.error(f"Failed to create JobPosting object: {e}")
            # Return minimal valid object
            return JobPosting(
                title=data.get('title', 'Job Opening'),
                company=data.get('company', 'Unknown Company'),
                source_url=data.get('source_url', ''),
                retrieved_at=data.get('retrieved_at', datetime.now(timezone.utc).isoformat()),
                description=data.get('description', 'No description available')
            )

    def to_dict(self, job: JobPosting) -> Dict[str, Any]:
        """Convert JobPosting to dictionary"""
        result = asdict(job)
        
        # Handle nested objects
        if result.get('salary'):
            result['salary'] = asdict(job.salary) if job.salary else None
        if result.get('provenance'):
            result['provenance'] = asdict(job.provenance) if job.provenance else None
        
        return result


async def main():
    """Test the scraper"""
    scraper = JobScraper()
    
    # Test with a sample URL
    test_url = "https://www.example.com/job"  # Replace with actual job URL
    
    try:
        job = await scraper.scrape_job(test_url)
        job_dict = scraper.to_dict(job)
        
        print(json.dumps(job_dict, indent=2, default=str))
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())