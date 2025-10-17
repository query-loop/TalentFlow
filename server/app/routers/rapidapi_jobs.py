"""
FastAPI router for RapidAPI job search integration
Provides endpoints for real-time job data retrieval from multiple providers
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from app.utils.rapidapi_jobs import (
    JobSearchManager, 
    JobSearchProvider, 
    JobSearchQuery,
    StandardizedJob,
    get_recommended_providers
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuration - in production, use environment variables
RAPIDAPI_KEY = "your-rapidapi-key-here"  # Set from environment


class JobSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    job_type: Optional[str] = None  # full-time, part-time, contract, internship
    remote_only: bool = False
    date_posted: Optional[str] = None  # today, 3days, week, month
    limit: int = 10
    providers: Optional[List[str]] = None


class JobSearchResponse(BaseModel):
    jobs: List[Dict[str, Any]]
    total_found: int
    providers_used: List[str]
    query_info: Dict[str, Any]


def get_job_manager():
    """Dependency to get job search manager instance"""
    if not RAPIDAPI_KEY or RAPIDAPI_KEY == "your-rapidapi-key-here":
        raise HTTPException(
            status_code=500, 
            detail="RapidAPI key not configured. Please set RAPIDAPI_KEY environment variable."
        )
    return JobSearchManager(RAPIDAPI_KEY)


@router.get("/search", response_model=JobSearchResponse)
async def search_jobs(
    query: str = Query(..., description="Job search query (e.g., 'software engineer')"),
    location: Optional[str] = Query(None, description="Location filter (e.g., 'San Francisco, CA')"),
    job_type: Optional[str] = Query(None, description="Job type filter (full-time, part-time, contract, internship)"),
    remote_only: bool = Query(False, description="Filter for remote jobs only"),
    date_posted: Optional[str] = Query(None, description="Date posted filter (today, 3days, week, month)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of jobs to return"),
    providers: Optional[str] = Query(None, description="Comma-separated list of providers (jsearch, jobs-api, reed-jobs)"),
    manager: JobSearchManager = Depends(get_job_manager)
):
    """
    Search for jobs across multiple RapidAPI providers
    
    Returns unified job results with deduplication and standardized format.
    """
    
    try:
        # Parse provider list
        provider_list = None
        if providers:
            provider_names = [p.strip().lower() for p in providers.split(",")]
            provider_list = []
            for name in provider_names:
                if name == "jsearch":
                    provider_list.append(JobSearchProvider.JSEARCH)
                elif name == "jobs-api":
                    provider_list.append(JobSearchProvider.JOBS_API)
                elif name == "reed-jobs":
                    provider_list.append(JobSearchProvider.REED_JOBS)
        
        # Perform search
        jobs = await manager.search_jobs_unified(
            query=query,
            location=location,
            job_type=job_type,
            limit=limit,
            providers=provider_list
        )
        
        # Convert to response format
        jobs_dict = manager.jobs_to_dict(jobs)
        
        used_providers = list(set(job.get("source", "Unknown") for job in jobs_dict))
        
        return JobSearchResponse(
            jobs=jobs_dict,
            total_found=len(jobs_dict),
            providers_used=used_providers,
            query_info={
                "query": query,
                "location": location,
                "job_type": job_type,
                "remote_only": remote_only,
                "date_posted": date_posted,
                "limit": limit
            }
        )
        
    except Exception as e:
        logger.error(f"Job search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs_post(
    request: JobSearchRequest,
    manager: JobSearchManager = Depends(get_job_manager)
):
    """
    Search for jobs using POST request with detailed parameters
    
    Supports more complex search parameters and provider selection.
    """
    
    try:
        # Parse provider list
        provider_list = None
        if request.providers:
            provider_list = []
            for name in request.providers:
                name = name.lower().strip()
                if name == "jsearch":
                    provider_list.append(JobSearchProvider.JSEARCH)
                elif name == "jobs-api":
                    provider_list.append(JobSearchProvider.JOBS_API)
                elif name == "reed-jobs":
                    provider_list.append(JobSearchProvider.REED_JOBS)
        
        # Perform search
        jobs = await manager.search_jobs_unified(
            query=request.query,
            location=request.location,
            job_type=request.job_type,
            limit=request.limit,
            providers=provider_list
        )
        
        # Convert to response format
        jobs_dict = manager.jobs_to_dict(jobs)
        
        used_providers = list(set(job.get("source", "Unknown") for job in jobs_dict))
        
        return JobSearchResponse(
            jobs=jobs_dict,
            total_found=len(jobs_dict),
            providers_used=used_providers,
            query_info={
                "query": request.query,
                "location": request.location,
                "job_type": request.job_type,
                "remote_only": request.remote_only,
                "date_posted": request.date_posted,
                "limit": request.limit
            }
        )
        
    except Exception as e:
        logger.error(f"Job search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")


@router.get("/providers")
async def get_available_providers():
    """
    Get information about available job search providers
    
    Returns details about each provider including free tier limits and features.
    """
    
    recommendations = get_recommended_providers()
    
    providers_info = {
        "available_providers": [
            {
                "id": "jsearch",
                "name": "JSearch",
                "description": "Comprehensive job search with global coverage",
                "free_tier_limit": 100,
                "rate_limit": 100,
                "features": ["Real-time data", "Detailed job info", "Global coverage", "Salary information"]
            },
            {
                "id": "jobs-api",
                "name": "Jobs API",
                "description": "Multi-board job aggregation service",
                "free_tier_limit": 100,
                "rate_limit": 500,
                "features": ["Multiple job boards", "Location filtering", "Remote job support", "Date filtering"]
            },
            {
                "id": "reed-jobs",
                "name": "Reed Jobs",
                "description": "UK-focused professional job search",
                "free_tier_limit": 75,
                "rate_limit": 1000,
                "features": ["UK market focus", "Professional roles", "Salary ranges", "Detailed descriptions"]
            }
        ],
        "recommendations": recommendations
    }
    
    return providers_info


@router.get("/job/{job_id}")
async def get_job_details(
    job_id: str,
    provider: str = Query("jsearch", description="Provider to fetch job details from"),
    manager: JobSearchManager = Depends(get_job_manager)
):
    """
    Get detailed information for a specific job
    
    Fetches comprehensive job details including full description and requirements.
    """
    
    try:
        # Map provider string to enum
        provider_enum = JobSearchProvider.JSEARCH
        if provider.lower() == "jobs-api":
            provider_enum = JobSearchProvider.JOBS_API
        elif provider.lower() == "reed-jobs":
            provider_enum = JobSearchProvider.REED_JOBS
        
        # Get job details (currently only supported by JSearch)
        if provider_enum != JobSearchProvider.JSEARCH:
            raise HTTPException(
                status_code=400, 
                detail="Job details endpoint currently only supported by JSearch provider"
            )
        
        from app.utils.rapidapi_jobs import RapidAPIJobClient
        
        async with RapidAPIJobClient(RAPIDAPI_KEY) as client:
            job = await client.get_job_details(job_id, provider_enum)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Convert to dict format
        job_dict = {
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
            "source": job.source,
            "raw_data": job.raw_data
        }
        
        return {"job": job_dict}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch job details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch job details: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint for job search service"""
    
    return {
        "status": "healthy",
        "service": "RapidAPI Job Search",
        "configured": RAPIDAPI_KEY != "your-rapidapi-key-here",
        "available_providers": ["jsearch", "jobs-api", "reed-jobs"]
    }