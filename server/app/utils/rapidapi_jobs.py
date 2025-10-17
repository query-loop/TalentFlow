"""
RapidAPI Job Search Integration
Provides unified interface for multiple job search APIs on RapidAPI platform.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import os

logger = logging.getLogger(__name__)


class JobSearchProvider(Enum):
    """Enumeration of supported job search providers.

    Note: Enum values use underscore naming to align with test expectations
    and external references (e.g. jobs_api instead of jobs-api).
    """
    JSEARCH = "jsearch"
    JOBS_API = "jobs_api"
    REED_JOBS = "reed_jobs"
    ADZUNA = "adzuna"


@dataclass
class JobSearchQuery:
    """Standardized job search query parameters"""
    query: str
    location: Optional[str] = None
    country: str = "US"
    job_type: Optional[str] = None  # full-time, part-time, contract, internship
    remote_jobs_only: bool = False
    date_posted: Optional[str] = None  # today, 3days, week, month
    employment_types: Optional[List[str]] = None
    job_requirements: Optional[List[str]] = None
    page: int = 1
    # Tests expect default of 20
    limit: int = 20


@dataclass
class StandardizedJob:
    """Standardized job data structure.

    Adjusted so that 'url' is optional (tests construct without it) and an
    explicit 'salary_currency' field is available (tests pass this kwarg).
    'currency' retained for backward compatibility; if only one provided,
    the other will mirror its value.
    """
    id: str
    title: str
    company: str
    location: str
    description: str
    # Optional to satisfy tests that omit it
    url: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    currency: Optional[str] = None  # legacy / alias
    job_type: Optional[str] = None
    remote: bool = False
    posted_date: Optional[str] = None
    apply_url: Optional[str] = None
    source: str = ""
    raw_data: Optional[Dict] = None

    def __post_init__(self):
        # Keep currency fields in sync
        if self.salary_currency and not self.currency:
            self.currency = self.salary_currency
        elif self.currency and not self.salary_currency:
            self.salary_currency = self.currency

        # If apply_url not provided but url exists, use it
        if not self.apply_url and self.url:
            self.apply_url = self.url


class RapidAPIJobClient:
    """Unified client for RapidAPI job search endpoints"""

    class _RateLimiter:
        """Simple time-based rate limiter (naive implementation)."""
        def __init__(self, rpm: int):
            self.interval = 60 / max(rpm, 1)
            self._last = 0.0
            self._lock = asyncio.Lock()

        async def acquire(self):
            async with self._lock:
                now = asyncio.get_event_loop().time()
                wait_for = self._last + self.interval - now
                if wait_for > 0:
                    await asyncio.sleep(wait_for)
                self._last = asyncio.get_event_loop().time()

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "",  # Will be set per provider
            "Content-Type": "application/json"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        # Default rate limiter (will be overridden per request)
        self.rate_limiter = self._RateLimiter(100)

        # Provider configurations
        self.providers = {
            JobSearchProvider.JSEARCH: {
                "host": "jsearch.p.rapidapi.com",
                "base_url": "https://jsearch.p.rapidapi.com",
                "endpoints": {
                    "search": "/search",
                    "job_details": "/job-details"
                },
                "rate_limit": 100,  # requests per minute
                "free_tier_limit": 100  # requests per month
            },
            JobSearchProvider.JOBS_API: {
                "host": "jobs-api14.p.rapidapi.com",
                "base_url": "https://jobs-api14.p.rapidapi.com",
                "endpoints": {
                    "search": "/list",
                    "job_details": "/get"
                },
                "rate_limit": 500,
                "free_tier_limit": 100
            },
            JobSearchProvider.REED_JOBS: {
                "host": "reed-jobs-search.p.rapidapi.com",
                "base_url": "https://reed-jobs-search.p.rapidapi.com",
                "endpoints": {
                    "search": "/search"
                },
                "rate_limit": 1000,
                "free_tier_limit": 75
            }
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_jobs(
        self, 
        query: JobSearchQuery, 
        provider: JobSearchProvider = JobSearchProvider.JSEARCH
    ) -> List[StandardizedJob]:
        """Search for jobs using specified provider"""
        
        if not self.session:
            raise RuntimeError("Client must be used as async context manager")
        
        provider_config = self.providers[provider]
        headers = self.base_headers.copy()
        headers["X-RapidAPI-Host"] = provider_config["host"]
        
        try:
            if provider == JobSearchProvider.JSEARCH:
                return await self._search_jsearch(query, provider_config, headers)
            elif provider == JobSearchProvider.JOBS_API:
                return await self._search_jobs_api(query, provider_config, headers)
            elif provider == JobSearchProvider.REED_JOBS:
                return await self._search_reed_jobs(query, provider_config, headers)
            else:
                raise ValueError(f"Provider {provider} not implemented")
                
        except Exception as e:
            logger.error(f"Job search failed for provider {provider}: {e}")
            return []
    
    async def _search_jsearch(
        self, 
        query: JobSearchQuery, 
        config: Dict, 
        headers: Dict
    ) -> List[StandardizedJob]:
        """Search using JSearch API"""
        
        params = {
            "query": query.query,
            "page": query.page,
            "num_pages": "1"
        }
        
        if query.location:
            params["location"] = query.location
        if query.remote_jobs_only:
            params["remote_jobs_only"] = "true"
        if query.date_posted:
            params["date_posted"] = query.date_posted
        if query.job_type:
            params["employment_types"] = query.job_type.upper()
        
        url = f"{config['base_url']}{config['endpoints']['search']}"
        
        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                logger.error(f"JSearch API error: {response.status}")
                return []
            
            data = await response.json()
            jobs = data.get("data", [])
            
            return [self._parse_jsearch_job(job) for job in jobs]
    
    async def _search_jobs_api(
        self, 
        query: JobSearchQuery, 
        config: Dict, 
        headers: Dict
    ) -> List[StandardizedJob]:
        """Search using Jobs API"""
        
        params = {
            "query": query.query,
            "location": query.location or "",
            "distance": "1.0",
            "language": "en_GB",
            "remoteOnly": "true" if query.remote_jobs_only else "false",
            "datePosted": query.date_posted or "month",
            "page": str(query.page)
        }
        
        url = f"{config['base_url']}{config['endpoints']['search']}"
        
        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                logger.error(f"Jobs API error: {response.status}")
                return []
            
            data = await response.json()
            jobs = data.get("jobs", [])
            
            return [self._parse_jobs_api_job(job) for job in jobs]
    
    async def _search_reed_jobs(
        self, 
        query: JobSearchQuery, 
        config: Dict, 
        headers: Dict
    ) -> List[StandardizedJob]:
        """Search using Reed Jobs API"""
        
        params = {
            "keywords": query.query,
            "location": query.location or "",
            "distanceFromLocation": "10",
            "permanent": "true" if query.job_type == "full-time" else "false",
            "resultsToTake": str(query.limit),
            "resultsToSkip": str((query.page - 1) * query.limit)
        }
        
        url = f"{config['base_url']}{config['endpoints']['search']}"
        
        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                logger.error(f"Reed Jobs API error: {response.status}")
                return []
            
            data = await response.json()
            jobs = data.get("results", [])
            
            return [self._parse_reed_job(job) for job in jobs]
    
    def _parse_jsearch_job(self, job_data: Dict) -> StandardizedJob:
        """Parse JSearch job data to standardized format"""
        
        return StandardizedJob(
            id=job_data.get("job_id", ""),
            title=job_data.get("job_title", ""),
            company=job_data.get("employer_name", ""),
            location=f"{job_data.get('job_city', '')}, {job_data.get('job_state', '')}, {job_data.get('job_country', '')}".strip(", "),
            description=job_data.get("job_description", ""),
            url=job_data.get("job_apply_link", ""),
            salary_min=job_data.get("job_min_salary"),
            salary_max=job_data.get("job_max_salary"),
            currency=job_data.get("job_salary_currency"),
            job_type=job_data.get("job_employment_type", "").lower(),
            remote=job_data.get("job_is_remote", False),
            posted_date=job_data.get("job_posted_at_datetime_utc"),
            apply_url=job_data.get("job_apply_link"),
            source="JSearch",
            raw_data=job_data
        )
    
    def _parse_jobs_api_job(self, job_data: Dict) -> StandardizedJob:
        """Parse Jobs API job data to standardized format"""
        
        return StandardizedJob(
            id=job_data.get("id", ""),
            title=job_data.get("title", ""),
            company=job_data.get("company", ""),
            location=job_data.get("location", ""),
            description=job_data.get("description", ""),
            url=job_data.get("url", ""),
            salary_min=self._extract_salary_min(job_data.get("salary", "")),
            salary_max=self._extract_salary_max(job_data.get("salary", "")),
            job_type=job_data.get("jobType", "").lower(),
            remote=job_data.get("remote", False),
            posted_date=job_data.get("datePosted"),
            apply_url=job_data.get("url"),
            source="Jobs API",
            raw_data=job_data
        )
    
    def _parse_reed_job(self, job_data: Dict) -> StandardizedJob:
        """Parse Reed Jobs job data to standardized format"""
        
        return StandardizedJob(
            id=str(job_data.get("jobId", "")),
            title=job_data.get("jobTitle", ""),
            company=job_data.get("employerName", ""),
            location=job_data.get("locationName", ""),
            description=job_data.get("jobDescription", ""),
            url=job_data.get("jobUrl", ""),
            salary_min=job_data.get("minimumSalary"),
            salary_max=job_data.get("maximumSalary"),
            currency="GBP",  # Reed is UK-focused
            job_type=job_data.get("jobType", "").lower(),
            posted_date=job_data.get("date"),
            apply_url=job_data.get("jobUrl"),
            source="Reed Jobs",
            raw_data=job_data
        )
    
    def _extract_salary_min(self, salary_str: str) -> Optional[int]:
        """Extract minimum salary from salary string"""
        if not salary_str:
            return None
        
        import re
        numbers = re.findall(r'\d+', salary_str.replace(',', ''))
        return int(numbers[0]) if numbers else None
    
    def _extract_salary_max(self, salary_str: str) -> Optional[int]:
        """Extract maximum salary from salary string"""
        if not salary_str:
            return None
        
        import re
        numbers = re.findall(r'\d+', salary_str.replace(',', ''))
        return int(numbers[-1]) if len(numbers) > 1 else None
    
    async def get_job_details(
        self, 
        job_id: str, 
        provider: JobSearchProvider = JobSearchProvider.JSEARCH
    ) -> Optional[StandardizedJob]:
        """Get detailed job information by ID"""
        
        if not self.session:
            raise RuntimeError("Client must be used as async context manager")
        
        provider_config = self.providers[provider]
        headers = self.base_headers.copy()
        headers["X-RapidAPI-Host"] = provider_config["host"]
        
        if provider == JobSearchProvider.JSEARCH:
            params = {"job_id": job_id}
            url = f"{provider_config['base_url']}{provider_config['endpoints']['job_details']}"
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    logger.error(f"Job details fetch failed: {response.status}")
                    return None
                
                data = await response.json()
                job_data = data.get("data", [])
                
                if job_data:
                    return self._parse_jsearch_job(job_data[0])
        
        return None
    
    async def search_multiple_providers(
        self, 
        query: JobSearchQuery, 
        providers: List[JobSearchProvider] = None
    ) -> Dict[JobSearchProvider, List[StandardizedJob]]:
        """Search across multiple providers simultaneously"""
        
        if providers is None:
            providers = list(JobSearchProvider)
        
        tasks = []
        for provider in providers:
            task = self.search_jobs(query, provider)
            tasks.append((provider, task))
        
        results = {}
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (provider, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                logger.error(f"Provider {provider} failed: {result}")
                results[provider] = []
            else:
                results[provider] = result
        
        return results


class JobSearchManager:
    """High-level manager for job search operations"""
    
    def __init__(self, rapidapi_key: Optional[str] = None):
        # Allow env var fallback
        key = rapidapi_key or os.getenv("RAPIDAPI_KEY")
        if not key:
            raise ValueError("RapidAPI key must be provided either as argument or RAPIDAPI_KEY env variable")
        self.rapidapi_key = key
        # Alias to satisfy tests expecting 'api_key'
        self.api_key = key
        self.default_provider = JobSearchProvider.JSEARCH
        self.cache: Dict[str, Any] = {}
        self.cache_duration = timedelta(hours=1)
    
    async def search_jobs_unified(
        self, 
        query: str, 
        location: str = None, 
        job_type: str = None,
        limit: int = 20,
        providers: List[JobSearchProvider] = None
    ) -> List[StandardizedJob]:
        """Unified job search across multiple providers with deduplication"""
        
        search_query = JobSearchQuery(
            query=query,
            location=location,
            job_type=job_type,
            limit=limit
        )
        
        # Check cache
        cache_key = f"{query}_{location}_{job_type}_{limit}"
        if cache_key in self.cache:
            cached_time, cached_jobs = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                return cached_jobs
        
        # Search across providers
        async with RapidAPIJobClient(self.rapidapi_key) as client:
            results = await client.search_multiple_providers(search_query, providers)
        
        # Combine and deduplicate results
        all_jobs = []
        seen_jobs = set()
        
        for provider, jobs in results.items():
            for job in jobs:
                # Simple deduplication based on title + company
                job_key = f"{job.title.lower()}_{job.company.lower()}"
                if job_key not in seen_jobs:
                    seen_jobs.add(job_key)
                    all_jobs.append(job)
        
        # Sort by relevance (you can implement custom scoring)
        all_jobs = sorted(all_jobs, key=lambda x: len(x.description), reverse=True)[:limit]
        
        # Cache results
        self.cache[cache_key] = (datetime.now(), all_jobs)
        
        return all_jobs
    
    def jobs_to_dict(self, jobs: List[StandardizedJob]) -> List[Dict]:
        """Convert StandardizedJob objects to dictionaries"""
        return [
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "description": job.description,
                "url": job.url,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "currency": job.currency,
                "job_type": job.job_type,
                "remote": job.remote,
                "posted_date": job.posted_date,
                "apply_url": job.apply_url,
                "source": job.source
            }
            for job in jobs
        ]


# Usage examples and utility functions
async def example_usage():
    """Example usage of the RapidAPI job search client"""
    
    api_key = "your-rapidapi-key-here"
    
    # Basic search
    async with RapidAPIJobClient(api_key) as client:
        query = JobSearchQuery(
            query="software engineer",
            location="San Francisco, CA",
            job_type="full-time",
            remote_jobs_only=False,
            limit=10
        )
        
        jobs = await client.search_jobs(query, JobSearchProvider.JSEARCH)
        
        for job in jobs:
            print(f"Title: {job.title}")
            print(f"Company: {job.company}")
            print(f"Location: {job.location}")
            print(f"URL: {job.url}")
            print(f"Remote: {job.remote}")
            print("-" * 50)
    
    # Multi-provider search with manager
    manager = JobSearchManager(api_key)
    
    unified_jobs = await manager.search_jobs_unified(
        query="python developer",
        location="New York, NY",
        job_type="full-time",
        limit=25,
        providers=[JobSearchProvider.JSEARCH, JobSearchProvider.JOBS_API]
    )
    
    jobs_dict = manager.jobs_to_dict(unified_jobs)
    return jobs_dict


def get_recommended_providers():
    """Get recommended free/freemium RapidAPI job search providers"""
    
    recommendations = {
        "best_free": {
            "provider": JobSearchProvider.JSEARCH,
            "reason": "Most comprehensive free tier with 100 requests/month",
            "features": ["Real-time data", "Detailed job info", "Global coverage", "Easy integration"]
        },
        "best_coverage": {
            "provider": JobSearchProvider.JOBS_API,
            "reason": "Good coverage with 100 free requests/month",
            "features": ["Multiple job boards", "Salary info", "Location filtering", "Remote job support"]
        },
        "uk_focused": {
            "provider": JobSearchProvider.REED_JOBS,
            "reason": "Best for UK market with 75 free requests/month",
            "features": ["UK job market", "Detailed descriptions", "Salary ranges", "Professional roles"]
        }
    }
    
    return recommendations


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())