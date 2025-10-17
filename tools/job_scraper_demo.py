#!/usr/bin/env python3
"""
Demo version of the job scraper that works with existing TalentFlow dependencies.
This demonstrates the core extraction logic without requiring additional packages.
"""

import json
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
from pathlib import Path
import asyncio

# Mock the external dependencies for demo
class MockPlaywright:
    pass

try:
    import jsonschema
except ImportError:
    jsonschema = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JobScraperDemo:
    """Demo job scraper using the existing fetch infrastructure"""
    
    def __init__(self, schema_path: Optional[str] = None):
        self.schema_path = schema_path or str(Path(__file__).parent.parent / "contracts" / "schemas" / "job_scraper.json")
        self.schema = self._load_schema()
        
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

    def scrape_job_with_html(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        Scrape job data from HTML content (for integration with existing fetch)
        This works with the current TalentFlow /api/fetch endpoint
        """
        logger.info(f"Parsing job data from {url}")
        
        # Parse HTML content
        try:
            from html.parser import HTMLParser
            parser = JobHTMLParser()
            parser.feed(html_content)
            
            # Extract using multiple methods
            json_ld_data = self._extract_json_ld_from_html(html_content)
            microdata = self._extract_microdata_from_html(html_content)
            dom_data = self._extract_dom_from_html(html_content, parser)
            regex_data = self._extract_regex_fallbacks(html_content)
            
            # Merge data with priority
            field_sources = {}
            merged_data = self._merge_extraction_data(
                json_ld_data, microdata, dom_data, regex_data, field_sources
            )
            
            # Add metadata
            merged_data.update({
                'source_url': url,
                'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'provenance': {
                    'extraction_method': self._determine_primary_method(json_ld_data, microdata, dom_data),
                    'confidence_score': self._calculate_confidence(json_ld_data, microdata, dom_data),
                    'field_sources': field_sources,
                    'warnings': []
                }
            })
            
            # Validate and repair
            validated_data = self._validate_and_repair(merged_data)
            
            return validated_data
            
        except Exception as e:
            logger.error(f"Failed to parse job data: {e}")
            return self._create_fallback_result(url, html_content)

    def _extract_json_ld_from_html(self, html: str) -> Dict[str, Any]:
        """Extract JobPosting from JSON-LD in HTML"""
        import re
        
        # Find JSON-LD scripts
        script_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, html, re.IGNORECASE | re.DOTALL)
        
        for script_content in scripts:
            try:
                data = json.loads(script_content.strip())
                
                # Handle both single objects and arrays
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    if item.get('@type') == 'JobPosting':
                        return self._parse_json_ld_job_posting(item)
                        
            except json.JSONDecodeError:
                continue
                
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
        
        return result

    def _extract_microdata_from_html(self, html: str) -> Dict[str, Any]:
        """Extract microdata from HTML"""
        # Simplified microdata extraction using regex
        result = {}
        
        # Look for microdata properties
        itemprop_pattern = r'<[^>]*itemprop=["\']([^"\']*)["\'][^>]*(?:content=["\']([^"\']*)["\']|>([^<]*))'
        matches = re.findall(itemprop_pattern, html, re.IGNORECASE)
        
        for prop_name, content_attr, text_content in matches:
            content = content_attr or text_content
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
        
        return result

    def _extract_dom_from_html(self, html: str, parser=None) -> Dict[str, Any]:
        """Extract job data using DOM patterns in HTML"""
        result = {}
        
        # Title extraction patterns
        title_patterns = [
            r'<h1[^>]*class=["\'][^"\']*job[^"\']*["\'][^>]*>([^<]+)</h1>',
            r'<h1[^>]*class=["\'][^"\']*title[^"\']*["\'][^>]*>([^<]+)</h1>',
            r'<h1[^>]*>([^<]+)</h1>',
            r'<title>([^<|]+)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match and len(match.group(1).strip()) > 0:
                result['title'] = match.group(1).strip()
                break
        
        # Company extraction patterns
        company_patterns = [
            r'<[^>]*class=["\'][^"\']*company[^"\']*["\'][^>]*>([^<]+)</[^>]*>',
            r'<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)["\']',
            r'<[^>]*class=["\'][^"\']*employer[^"\']*["\'][^>]*>([^<]+)</[^>]*>'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match and len(match.group(1).strip()) > 0:
                result['company'] = match.group(1).strip()
                break
        
        # Location extraction
        location_patterns = [
            r'<[^>]*class=["\'][^"\']*location[^"\']*["\'][^>]*>([^<]+)</[^>]*>',
            r'<[^>]*data-testid=["\'][^"\']*location[^"\']*["\'][^>]*>([^<]+)</[^>]*>'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match and len(match.group(1).strip()) > 0:
                result['location'] = match.group(1).strip()
                break
        
        # Description from main content
        desc_patterns = [
            r'<[^>]*class=["\'][^"\']*(?:job-desc|description)[^"\']*["\'][^>]*>(.*?)</[^>]*>',
            r'<main[^>]*>(.*?)</main>',
            r'<article[^>]*>(.*?)</article>'
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                # Clean HTML tags
                desc = re.sub(r'<[^>]+>', ' ', match.group(1))
                desc = re.sub(r'\s+', ' ', desc).strip()
                if len(desc) > 50:
                    result['description'] = desc
                    break
        
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
            # Require currency/unit hints in the raw match to avoid dates like "2025-01-15"
            raw = salary_match.group(0)
            has_hint = (
                ('$' in raw)
                or ('usd' in raw.lower())
                or ('k' in raw.lower())
                or re.search(r'\b(per|hour|year|annual|month|salary|compensation|pay)\b', raw, re.IGNORECASE)
            )
            if has_hint:
                try:
                    min_sal = float(salary_match.group(1).replace(',', ''))
                    max_sal = float(salary_match.group(2).replace(',', ''))
                    period = salary_match.group(3) or 'yearly'

                    # Convert K notation
                    if 'k' in raw.lower():
                        min_sal *= 1000
                        max_sal *= 1000

                    result['salary'] = {
                        'min': min_sal,
                        'max': max_sal,
                        'currency': 'USD',
                        'period': 'yearly' if period and period.lower() in ['year', 'annual'] else 'hourly' if period and period.lower() == 'hour' else 'yearly'
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

    def _determine_primary_method(self, json_ld: Dict, microdata: Dict, dom: Dict) -> str:
        """Determine the primary extraction method used"""
        if json_ld:
            return 'json-ld'
        elif microdata:
            return 'microdata'
        else:
            return 'dom-selectors'

    def _calculate_confidence(self, json_ld: Dict, microdata: Dict, dom: Dict) -> float:
        """Calculate confidence score based on extraction methods"""
        if json_ld:
            return 0.9
        elif microdata:
            return 0.8
        elif dom:
            return 0.6
        else:
            return 0.4

    def _normalize_employment_type(self, emp_type: str) -> Optional[str]:
        """Normalize employment type to schema enum"""  
        if not emp_type:
            return None
        
        emp_type = emp_type.lower().strip()
        
        return self.employment_type_map.get(emp_type, emp_type if emp_type in [
            'full-time', 'part-time', 'contract', 'temporary', 'internship', 'freelance'
        ] else None)

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date string to ISO format"""
        if not date_str:
            return None
        
        try:
            # Handle common formats - simplified version
            from datetime import datetime
            # Try parsing common formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%B %d, %Y']:
                try:
                    parsed_date = datetime.strptime(date_str.strip(), fmt)
                    return parsed_date.date().isoformat()
                except ValueError:
                    continue
        except:
            pass
        
        return None

    def _validate_and_repair(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data and attempt repairs"""
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
            data['description'] = f"Job opening at {data.get('company', 'Company')} for {data.get('title', 'Position')}"
            warnings.append("Description missing, used minimal default")
        
        # Update warnings
        if 'provenance' in data:
            data['provenance']['warnings'] = warnings
        
        return data

    def _create_fallback_result(self, url: str, html: str) -> Dict[str, Any]:
        """Create minimal fallback result when parsing fails"""
        # Try to get basic info from HTML
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Job Opening"
        
        # Guess company from URL
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ''
            company = hostname.split('.')[0].title() if hostname else "Unknown Company"
        except:
            company = "Unknown Company"
        
        return {
            'title': title,
            'company': company,
            'source_url': url,
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'description': f"Job opening at {company}",
            'provenance': {
                'extraction_method': 'fallback',
                'confidence_score': 0.2,
                'field_sources': {'title': 'fallback', 'company': 'fallback'},
                'warnings': ['Extraction failed, using fallback data']
            }
        }


class JobHTMLParser:
    """Simple HTML parser helper"""
    def __init__(self):
        self.text_content = ""
    
    def feed(self, html):
        # Simple text extraction
        self.text_content = re.sub(r'<[^>]+>', ' ', html)
        self.text_content = re.sub(r'\s+', ' ', self.text_content).strip()


# Demo CLI
def main():
    """Demo the scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Demo job scraper")
    parser.add_argument("--url", required=True, help="Job URL")
    parser.add_argument("--out", required=True, help="Output file")
    parser.add_argument("--html", help="HTML file to parse (for testing)")
    
    args = parser.parse_args()
    
    scraper = JobScraperDemo()
    
    if args.html:
        # Test with local HTML file
        with open(args.html, 'r', encoding='utf-8') as f:
            html_content = f.read()
    else:
        # Would use the existing TalentFlow fetch here
        html_content = f"<title>Demo Job at Demo Company</title><h1>Software Engineer</h1><div class='company-name'>TechCorp</div>"
    
    result = scraper.scrape_job_with_html(args.url, html_content)
    
    # Save result
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Job data extracted and saved to {args.out}")
    print(f"Title: {result.get('title')}")
    print(f"Company: {result.get('company')}")
    print(f"Method: {result.get('provenance', {}).get('extraction_method')}")


if __name__ == "__main__":
    main()