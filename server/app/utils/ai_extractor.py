from __future__ import annotations

"""
AI-Powered Dynamic Job Extractor
Intelligently discovers and extracts job-related content without static selectors.
"""

import re
from .lever_extractor import LeverJobExtractor
import math
from typing import Any, Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass
from collections import Counter


@dataclass
class ElementScore:
    """Scoring data for DOM elements."""
    element: Any  # BeautifulSoup element
    relevance_score: float
    content_type: str  # 'title', 'company', 'description', etc.
    confidence: float
    text_content: str
    reasons: List[str]


class AIJobExtractor:
    """
    Intelligent job content extractor that analyzes DOM structure 
    and content to identify relevant information dynamically.
    """
    
    def __init__(self):
        # Initialize specialized extractors
        self.lever_extractor = LeverJobExtractor()
        
        # Job-related keywords for semantic analysis
        self.job_keywords = {
            'title': [
                'engineer', 'developer', 'manager', 'analyst', 'designer', 'architect',
                'specialist', 'coordinator', 'director', 'lead', 'senior', 'junior',
                'intern', 'position', 'role', 'job', 'career', 'opportunity'
            ],
            'company': [
                'company', 'corporation', 'inc', 'llc', 'ltd', 'technologies', 'systems',
                'solutions', 'group', 'enterprises', 'consulting', 'services'
            ],
            'location': [
                'location', 'city', 'state', 'country', 'remote', 'hybrid', 'onsite',
                'office', 'headquarters', 'based', 'street', 'avenue', 'drive'
            ],
            'employment': [
                'full-time', 'part-time', 'contract', 'temporary', 'permanent',
                'freelance', 'intern', 'entry-level', 'experienced', 'senior'
            ],
            'requirements': [
                'requirements', 'qualifications', 'skills', 'experience', 'education',
                'degree', 'certification', 'knowledge', 'background', 'must have'
            ],
            'benefits': [
                'benefits', 'compensation', 'salary', 'package', 'insurance', 'health',
                'dental', 'vision', '401k', 'vacation', 'pto', 'perks', 'bonus'
            ]
        }
        
        # Link classification keywords
        self.link_keywords = {
            'apply': ['apply', 'application', 'submit', 'join', 'career', 'jobs'],
            'company': ['about', 'company', 'organization', 'team', 'culture', 'mission'],
            'benefits': ['benefits', 'perks', 'compensation', 'package', 'salary'],
            'requirements': ['requirements', 'qualifications', 'skills', 'education'],
            'contact': ['contact', 'email', 'phone', 'reach', 'get in touch']
        }
        
        # HTML structure indicators
        self.structure_indicators = {
            'title': ['h1', 'h2', 'h3', 'title'],
            'header': ['header', 'top', 'title', 'heading'],
            'main_content': ['main', 'content', 'body', 'description', 'details'],
            'sidebar': ['sidebar', 'aside', 'meta', 'info'],
            'footer': ['footer', 'bottom', 'contact']
        }

    def extract_dynamically(self, url: str, html: str) -> Dict[str, Any]:
        """
        Main extraction method that adapts to any job posting structure.
        """
        # Check if this is a Lever job posting for specialized extraction
        if self._is_lever_job(url, html):
            print(f"🎯 Detected Lever job posting - using specialized extractor")
            lever_result = self.lever_extractor.extract_lever_job(url, html)
            
            # Enhance with AI-powered link extraction for any missed content
            ai_links = self._extract_dynamic_links(html, url)
            if ai_links:
                lever_result.setdefault('links', {})
                for category, links in ai_links.items():
                    lever_result['links'].setdefault(category, []).extend(links)
            
            return lever_result
        
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return self._fallback_extraction(html, url)

    def _is_lever_job(self, url: str, html: str) -> bool:
        """Check if this is a Lever job posting."""
        if 'jobs.lever.co' in url.lower():
            return True
        # Check HTML content for Lever indicators
        lever_indicators = [
            'lever.co',
            'posting-headline',
            'posting-categories',
            'lever-application',
            'data-qa="job-'
        ]
        
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in lever_indicators)
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove noise elements
        self._clean_soup(soup)
        
        # Analyze page structure
        page_structure = self._analyze_page_structure(soup)
        
        # Find all potential job elements
        candidates = self._find_content_candidates(soup)
        
        # Score and classify elements
        scored_elements = self._score_elements(candidates, url)
        
        # Extract structured data
        job_data = self._extract_structured_data(scored_elements, page_structure)
        
        # Find and classify links
        job_data['links'] = self._extract_dynamic_links(soup, url)
        
        # Add metadata
        job_data.update({
            'source_url': url,
            'extraction_method': 'ai_dynamic',
            'confidence_score': self._calculate_overall_confidence(scored_elements),
            'discovered_elements': len(scored_elements),
            'page_structure': page_structure
        })
        
        return job_data

    def _clean_soup(self, soup):
        """Remove noise elements that don't contribute to job content."""
        noise_selectors = [
            'script', 'style', 'nav', 'footer', 'header[role="banner"]',
            '.advertisement', '.ads', '.cookie', '.popup', '.modal',
            '[class*="ad-"]', '[id*="ad-"]', '.social-media', '.share'
        ]
        
        for selector in noise_selectors:
            for element in soup.select(selector):
                element.decompose()

    def _analyze_page_structure(self, soup) -> Dict[str, Any]:
        """Analyze the overall structure and layout of the page."""
        structure = {
            'has_header': bool(soup.find(['header', '[role="banner"]'])),
            'has_main': bool(soup.find(['main', '[role="main"]'])),
            'has_aside': bool(soup.find(['aside', '[role="complementary"]'])),
            'heading_hierarchy': [],
            'content_sections': 0,
            'total_links': len(soup.find_all('a', href=True)),
            'total_text_length': len(soup.get_text()),
            'dominant_content_area': None
        }
        
        # Analyze heading hierarchy
        for level in range(1, 7):
            headings = soup.find_all(f'h{level}')
            if headings:
                structure['heading_hierarchy'].append({
                    'level': level,
                    'count': len(headings),
                    'texts': [h.get_text(strip=True) for h in headings[:3]]  # Sample first 3
                })
        
        # Find dominant content area
        content_areas = soup.find_all(['main', 'article', '[role="main"]', '.content', '#content'])
        if content_areas:
            largest_area = max(content_areas, key=lambda x: len(x.get_text()))
            structure['dominant_content_area'] = largest_area
            structure['content_sections'] = len(largest_area.find_all(['section', 'div', 'article']))
        
        return structure

    def _find_content_candidates(self, soup) -> List[Any]:
        """Find all elements that could potentially contain job information."""
        candidates = []
        
        # Text-heavy elements
        for tag in ['p', 'div', 'span', 'section', 'article']:
            elements = soup.find_all(tag)
            for element in elements:
                text = element.get_text(strip=True)
                if len(text) > 20:  # Minimum meaningful content
                    candidates.append(element)
        
        # Headings
        for level in range(1, 7):
            candidates.extend(soup.find_all(f'h{level}'))
        
        # List items (often contain requirements, benefits)
        candidates.extend(soup.find_all('li'))
        
        # Form elements (job application related)
        candidates.extend(soup.find_all(['form', 'input', 'button']))
        
        return candidates

    def _score_elements(self, candidates: List[Any], url: str) -> List[ElementScore]:
        """Score elements based on their likelihood of containing job information."""
        scored_elements = []
        
        for element in candidates:
            score_data = self._calculate_element_score(element, url)
            if score_data.relevance_score > 0.1:  # Filter out very low scores
                scored_elements.append(score_data)
        
        # Sort by relevance score
        scored_elements.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return scored_elements

    def _calculate_element_score(self, element, url: str) -> ElementScore:
        """Calculate relevance score for a single element."""
        text = element.get_text(strip=True).lower()
        tag_name = element.name.lower()
        classes = ' '.join(element.get('class', [])).lower()
        element_id = element.get('id', '').lower()
        
        score = 0.0
        content_type = 'unknown'
        confidence = 0.0
        reasons = []
        
        # Heading bonus
        if tag_name in ['h1', 'h2', 'h3']:
            score += 2.0
            reasons.append(f'heading_{tag_name}')
        
        # Length scoring (sweet spot for job content)
        text_length = len(text)
        if 50 <= text_length <= 2000:
            score += 1.0
            reasons.append('optimal_length')
        elif text_length > 2000:
            score += 0.5
            reasons.append('long_content')
        
        # Keyword analysis for each category
        best_category = None
        best_category_score = 0
        
        for category, keywords in self.job_keywords.items():
            category_score = 0
            category_matches = 0
            
            for keyword in keywords:
                if keyword in text:
                    category_score += 1
                    category_matches += 1
                
                # Bonus for keyword in class/id
                if keyword in classes or keyword in element_id:
                    category_score += 2
                    category_matches += 1
            
            if category_score > best_category_score:
                best_category_score = category_score
                best_category = category
            
            if category_matches > 0:
                score += category_score * 0.5
                reasons.append(f'{category}_keywords_{category_matches}')
        
        content_type = best_category or 'general'
        
        # Structural indicators
        combined_attrs = f"{classes} {element_id}".lower()
        for indicator_type, indicators in self.structure_indicators.items():
            for indicator in indicators:
                if indicator in combined_attrs:
                    score += 1.5
                    reasons.append(f'structure_{indicator_type}')
                    break
        
        # Position bias (elements higher up are often more important)
        position_score = self._calculate_position_score(element)
        score += position_score
        if position_score > 0:
            reasons.append('good_position')
        
        # Calculate confidence based on multiple signals
        confidence = min(1.0, score / 10.0)  # Normalize to 0-1
        
        return ElementScore(
            element=element,
            relevance_score=score,
            content_type=content_type,
            confidence=confidence,
            text_content=element.get_text(strip=True),
            reasons=reasons
        )

    def _calculate_position_score(self, element) -> float:
        """Calculate score bonus based on element position in DOM."""
        try:
            # Count how many elements come before this one
            all_elements = element.find_parent().find_all() if element.find_parent() else []
            if not all_elements:
                return 0.0
            
            position = 0
            for i, elem in enumerate(all_elements):
                if elem == element:
                    position = i
                    break
            
            # Earlier elements get higher scores
            total_elements = len(all_elements)
            if total_elements > 0:
                return max(0, 2.0 - (position / total_elements) * 2.0)
            
        except Exception:
            pass
        
        return 0.0

    def _extract_structured_data(self, scored_elements: List[ElementScore], 
                                 page_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured job data from scored elements."""
        job_data = {
            'title': None,
            'company': None,
            'location': None,
            'description': None,
            'requirements': [],
            'benefits': [],
            'employment_type': None,
            'salary': None
        }
        
        # Group elements by content type
        by_type = {}
        for element in scored_elements:
            content_type = element.content_type
            if content_type not in by_type:
                by_type[content_type] = []
            by_type[content_type].append(element)
        
        # Extract title (highest scoring title-type element)
        if 'title' in by_type:
            best_title = max(by_type['title'], key=lambda x: x.relevance_score)
            job_data['title'] = best_title.text_content
        
        # Extract company (look for company-type or high-scoring short text)
        if 'company' in by_type:
            best_company = max(by_type['company'], key=lambda x: x.relevance_score)
            job_data['company'] = best_company.text_content
        
        # Extract location
        if 'location' in by_type:
            best_location = max(by_type['location'], key=lambda x: x.relevance_score)
            job_data['location'] = best_location.text_content
        
        # Extract description (longest high-scoring content)
        description_candidates = []
        for element in scored_elements:
            if (len(element.text_content) > 200 and 
                element.relevance_score > 1.0 and
                element.content_type in ['general', 'requirements', 'benefits']):
                description_candidates.append(element)
        
        if description_candidates:
            best_description = max(description_candidates, 
                                 key=lambda x: len(x.text_content) * x.relevance_score)
            job_data['description'] = best_description.text_content
        
        # Extract requirements and benefits from lists
        for element in scored_elements:
            if element.element.name == 'li':
                text = element.text_content
                if any(req in text.lower() for req in self.job_keywords['requirements']):
                    job_data['requirements'].append(text)
                elif any(ben in text.lower() for ben in self.job_keywords['benefits']):
                    job_data['benefits'].append(text)
        
        return job_data
    def _extract_dynamic_links(self, soup_or_html, base_url: str) -> Dict[str, List[Dict[str, str]]]:
        """Dynamically identify and classify relevant links."""
        links = {'apply': [], 'company': [], 'benefits': [], 'contact': [], 'other': []}
        
        # Handle both BeautifulSoup objects and HTML strings
        if isinstance(soup_or_html, str):
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(soup_or_html, 'html.parser')
            except ImportError:
                return links  # Return empty links if BeautifulSoup not available
        else:
            soup = soup_or_html
        
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '').strip()
            text = link.get_text(strip=True)
            
            if not href or href.startswith('#'):
                continue
            
            # Convert relative URLs to absolute
            if href.startswith('/') or href.startswith('./'):
                href = urljoin(base_url, href)
            
            # Classify link based on text and URL
            link_data = {
                'url': href,
                'text': text,
                'confidence': 0.0
            }
            
            # Analyze link context
            combined_text = f"{text} {href}".lower()
            
            best_category = 'other'
            best_score = 0
            
            for category, keywords in self.link_keywords.items():
                score = sum(1 for keyword in keywords if keyword in combined_text)
                if score > best_score:
                    best_score = score
                    best_category = category
            
            link_data['confidence'] = min(1.0, best_score / 3.0)
            links[best_category].append(link_data)
        
        # Sort each category by confidence
        for category in links:
            links[category].sort(key=lambda x: x['confidence'], reverse=True)
        
        return links

    def _calculate_overall_confidence(self, scored_elements: List[ElementScore]) -> float:
        """Calculate overall extraction confidence."""
        if not scored_elements:
            return 0.0
        
        # Average of top 5 scores
        top_scores = [elem.confidence for elem in scored_elements[:5]]
        return sum(top_scores) / len(top_scores)

    def _fallback_extraction(self, html: str, url: str) -> Dict[str, Any]:
        """Fallback extraction when BeautifulSoup is not available."""
        # Simple regex-based extraction as fallback
        title_match = re.search(r'<h[1-3][^>]*>([^<]+)</h[1-3]>', html, re.IGNORECASE)
        
        return {
            'title': title_match.group(1).strip() if title_match else None,
            'description': 'Fallback extraction - BeautifulSoup required for full AI analysis',
            'source_url': url,
            'extraction_method': 'fallback_regex',
            'confidence_score': 0.1,
            'links': {'other': []},
            'requirements': [],
            'benefits': []
        }