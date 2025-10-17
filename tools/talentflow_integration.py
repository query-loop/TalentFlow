"""
Integration module to connect the job scraper with TalentFlow's existing JD import workflow.
This enhances the frontend fetch endpoint with the production scraper.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import our scraper
from .job_scraper import JobScraper

logger = logging.getLogger(__name__)


class TalentFlowJobImporter:
    """Enhanced job importer using the production scraper"""
    
    def __init__(self, schema_path: Optional[str] = None):
        self.scraper = JobScraper(schema_path=schema_path)
    
    async def import_job_from_url(self, url: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Import job posting from URL and return in TalentFlow format.
        
        Returns:
            Dict with keys: company, role, location, source, jd, metadata
        """
        try:
            # Use the production scraper
            job_posting = await self.scraper.scrape_job(url, max_retries=max_retries)
            
            # Convert to TalentFlow format
            talent_flow_format = self._convert_to_talent_flow_format(job_posting)
            
            logger.info(f"Successfully imported job: {job_posting.title} at {job_posting.company}")
            
            return talent_flow_format
            
        except Exception as e:
            logger.error(f"Failed to import job from {url}: {str(e)}")
            raise

    def _convert_to_talent_flow_format(self, job_posting) -> Dict[str, Any]:
        """Convert JobPosting to TalentFlow JDItem format"""
        
        # Build description from structured data
        description_parts = []
        
        if job_posting.description:
            description_parts.append(job_posting.description)
        
        # Add structured sections
        if job_posting.responsibilities:
            description_parts.append("\nResponsibilities:")
            for resp in job_posting.responsibilities[:10]:  # Limit items
                description_parts.append(f"• {resp}")
        
        if job_posting.qualifications:
            description_parts.append("\nQualifications:")
            for qual in job_posting.qualifications[:10]:  # Limit items
                description_parts.append(f"• {qual}")
        
        if job_posting.skills:
            description_parts.append(f"\nKey Skills: {', '.join(job_posting.skills[:20])}")
        
        if job_posting.benefits:
            description_parts.append("\nBenefits:")
            for benefit in job_posting.benefits[:8]:  # Limit items
                description_parts.append(f"• {benefit}")
        
        if job_posting.salary:
            salary_text = f"Salary: "
            if job_posting.salary.min and job_posting.salary.max:
                salary_text += f"${job_posting.salary.min:,.0f} - ${job_posting.salary.max:,.0f}"
            elif job_posting.salary.min:
                salary_text += f"${job_posting.salary.min:,.0f}+"
            elif job_posting.salary.max:
                salary_text += f"Up to ${job_posting.salary.max:,.0f}"
            
            if job_posting.salary.period != 'yearly':
                salary_text += f" ({job_posting.salary.period})"
            
            description_parts.append(f"\n{salary_text}")
        
        full_description = "\n".join(description_parts)
        
        # Create metadata with scraper info
        metadata = {
            'scraper_version': '1.0',
            'extraction_method': job_posting.provenance.extraction_method if job_posting.provenance else 'unknown',
            'confidence_score': job_posting.provenance.confidence_score if job_posting.provenance else 0.5,
            'retrieved_at': job_posting.retrieved_at,
            'req_id': job_posting.req_id,
            'team': job_posting.team,
            'level': job_posting.level,
            'employment_type': job_posting.employment_type,
            'posted_date': job_posting.posted_date,
            'apply_url': job_posting.apply_url,
            'field_sources': job_posting.provenance.field_sources if job_posting.provenance else {},
            'warnings': job_posting.provenance.warnings if job_posting.provenance else []
        }
        
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        return {
            'company': job_posting.company,
            'role': job_posting.title,
            'location': job_posting.location,
            'source': job_posting.source_url,
            'jd': full_description,
            'metadata': metadata
        }


# FastAPI integration example for the backend
"""
Example integration with the existing FastAPI backend:

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .talentflow_integration import TalentFlowJobImporter

router = APIRouter()

class ImportJobRequest(BaseModel):
    url: str
    max_retries: int = 3

@router.post("/api/jd/import-enhanced")
async def import_job_enhanced(request: ImportJobRequest):
    '''Enhanced job import using production scraper'''
    try:
        importer = TalentFlowJobImporter()
        result = await importer.import_job_from_url(
            url=request.url,
            max_retries=request.max_retries
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
"""


# Frontend integration example
"""
Example integration with the existing frontend import logic:

async function importFromUrlEnhanced(url) {
    try {
        const response = await fetch('/api/jd/import-enhanced', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ url, max_retries: 3 })
        });
        
        if (!response.ok) {
            throw new Error(`Import failed: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Create JD item with enhanced metadata
        const item = {
            id: crypto.randomUUID(),
            company: result.company,
            role: result.role,
            location: result.location,
            source: result.source,
            jd: result.jd,
            metadata: result.metadata,
            createdAt: Date.now(),
            updatedAt: Date.now()
        };
        
        return item;
    } catch (error) {
        console.error('Enhanced import failed:', error);
        throw error;
    }
}
"""